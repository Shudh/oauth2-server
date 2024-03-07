import json
import os
import time
from flask import Blueprint, request, session, url_for, flash
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import db, User, OAuth2Client
from .oauth2 import authorization, require_oauth
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('home', __name__)


def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None


def save_token_to_file(access_token):
    # Use Railway's environment variable for the volume mount path
    file_path = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'access_token.txt')
    try:
        with open(file_path, 'w') as file:
            file.write(access_token)
        print(f'Access token saved to {file_path}')
    except IOError as e:
        print(f'Error writing to file: {e}')


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@bp.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        # if user is not just to log in, but need to head back to the auth page, then go for it
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect('/')
    user = current_user()
    if user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
    else:
        clients = []

    return render_template('home.html', user=user, clients=clients)


@bp.route('/new_home', methods=['GET', 'POST'])
def new_home():
    # Check if user is already logged in
    if current_user():
        return render_template('new_home.html', user=current_user())

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        action = request.form['action']

        if action == 'register':
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.')
                return redirect(url_for('home.new_home'))

            # Create new user with hashed password
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('home.new_home'))

        elif action == 'login':
            user = User.query.filter_by(username=username).first()

            # Verify password and log in user
            if user and check_password_hash(user.password_hash, password):
                session['id'] = user.id
                return redirect(url_for('home.new_home'))
            else:
                flash('Invalid username or password.')
                return redirect(url_for('home.new_home'))

    # If GET request or any other condition not met, show registration/login form
    return render_template('new_home.html')


@bp.route('/logout')
def logout():
    del session['id']
    flash('You have been logged out.')  # Flash a message to the user
    return redirect(url_for('home.new_home'))  # Redirect to the new_home endpoint
    # return redirect('/')


@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        # return redirect('/')
        return redirect(url_for('home.new_home'))  # Redirect to the new_home endpoint
    if request.method == 'GET':
        return render_template('create_client.html')

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = OAuth2Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        user_id=user.id,
    )

    form = request.form
    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    }
    client.set_client_metadata(client_metadata)

    if form['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()
    return redirect(url_for('home.new_home'))  # Redirect to the new_home endpoint
    # return redirect('/')


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    # Log the original request URL
    original_url = request.url
    print(f"Original request URL: {original_url}")

    # Forcibly replace 'http://' with 'https://' in the URL if needed (for debugging purposes)
    https_authorization_url = original_url.replace('http://', 'https://')
    print(f"Modified request URL: {https_authorization_url}")

    user = current_user()
    if not user:
        # Use the modified URL for the redirect for debugging
        return redirect(url_for('home.new_home', next=https_authorization_url))

    if request.method == 'GET':
        try:
            grant = authorization.get_consent_grant(end_user=user)
        except OAuth2Error as error:
            # Log the full error and stack trace
            print("OAuth2Error encountered: %s", error.description)
            # Consider how to handle the error; returning detailed errors to the browser is for debugging only
            return jsonify({'error': str(error)}), 400
        return render_template('authorize.html', user=user, grant=grant)

    # POST request handling remains unchanged
    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()

    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None

    return authorization.create_authorization_response(grant_user=grant_user)


@bp.route('/oauth/token', methods=['POST'])
def issue_token():
    # return authorization.create_token_response()
    response = authorization.create_token_response()
    response_data = response.get_data(as_text=True)
    json_data = json.loads(response_data)
    access_token = json_data.get('access_token', None)
    if access_token is not None:
        save_token_to_file(access_token)
    return response


@bp.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)


# This is added so that the resource can be checked without another resource server
from flask import request, jsonify
from werkzeug.exceptions import Unauthorized
from .models import db, OAuth2Token, User


def validate_bearer_token():
    authorization = request.headers.get("Authorization", None)
    if not authorization:
        raise Unauthorized(description="Authorization header is missing.")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise Unauthorized(description="Invalid authorization header format.")

    token_value = authorization[len(prefix):]
    token = OAuth2Token.query.filter_by(access_token=token_value).first()
    if not token or token.revoked:
        raise Unauthorized(description="Invalid or expired token.")

    # Fetch the user associated with the token
    user = User.query.get(token.user_id)
    if not user:
        raise Unauthorized(description="User not found.")

    # You might want to return user or other data along with token
    return token, user


@bp.route('/api/data')
def protected_data():
    try:
        token, user = validate_bearer_token()
        # Now you have the user object as well, you can use it as needed
        return jsonify({"message": "This is protected data", "user_id": user.id, "username": user.username})
    except Unauthorized as e:
        return jsonify({"error": str(e)}), 401
