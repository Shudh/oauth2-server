# routes.py
import json
import os
import time
from flask import Blueprint, request, session, url_for, flash, send_from_directory, after_this_request, current_app
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import db, User, OAuth2Client
from .oauth2 import authorization, require_oauth
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from functools import wraps

bp = Blueprint('home', __name__)


def log_to_file(message):
    file_path = os.path.join(os.environ['RAILWAY_VOLUME_MOUNT_PATH'], 'app.log')
    try:
        with open(file_path, 'a') as log_file:
            log_file.write(message + "\n")
    except IOError as e:
        print(f'Error writing to file: {e}')


def detailed_logging(endpoint_func):
    @wraps(endpoint_func)
    def wrapper(*args, **kwargs):
        log_message = f'Incoming request to {request.path}\n'
        log_message += f'Method: {request.method}\n'
        log_message += f'Headers: {json.dumps(dict(request.headers), indent=2)}\n'
        log_message += f'Body: {request.get_data(as_text=True)}\n'

        log_to_file(log_message)

        @after_this_request
        def log_response(response):
            log_message = f'Outgoing response from {request.path}\n'
            log_message += f'Status: {response.status}\n'
            log_message += f'Headers: {json.dumps(dict(response.headers), indent=2)}\n'
            # Response body logging is not included here to avoid complexity and potential issues with binary data.
            log_to_file(log_message)
            return response

        return endpoint_func(*args, **kwargs)

    return wrapper


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


@bp.route('/files')
def list_files():
    directory = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    files = os.listdir(directory)
    files_list = '<ul>'
    for file in files:
        file_path = url_for('home.file',
                            filename=file)  # Adjust the 'home.file' based on your blueprint name if necessary
        files_list += f'<li><a href="{file_path}">{file}</a></li>'
    files_list += '</ul>'
    return files_list


@bp.route('/files/<filename>')
def file(filename):
    directory = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    return send_from_directory(directory, filename)


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
                # Now let the user give consent
                # return redirect(url_for('home.new_home'))
                # Redirect user to the stored URL or back to the new_home page if no redirect URL is set
                redirect_url = session.pop('post_login_redirect', url_for('home.new_home'))
                return redirect(redirect_url)
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
@detailed_logging
def authorize():
    # This state mismatch happens only when we go to google
    # Store the incoming state parameter
    incoming_state = request.args.get('state')
    session['gpt_state'] = incoming_state
    # Log the original request URL
    original_url = request.url
    print(f"Original request URL: {original_url}")

    # Forcibly replace 'http://' with 'https://' in the URL if needed (for debugging purposes)
    https_authorization_url = original_url.replace('http://', 'https://')
    print(f"Modified request URL: {https_authorization_url}")

    user = current_user()
    if not user:
        # This is added to redirect the user to consent page after he is logged in
        # Store the intended authorization URL in the session for later redirection
        session['post_login_redirect'] = https_authorization_url
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


# Shudh: working function with custom oauth commented to add a new function
# to handle google oauth too
# @bp.route('/oauth/token', methods=['POST'])
# @detailed_logging
# def issue_token():
#     # return authorization.create_token_response()
#     response = authorization.create_token_response()
#     response_data = response.get_data(as_text=True)
#     json_data = json.loads(response_data)
#     access_token = json_data.get('access_token', None)
#     if access_token is not None:
#         save_token_to_file(access_token)
#     return response

@bp.route('/oauth/token', methods=['POST'])
@detailed_logging
def issue_token():
    if 'oauth_flow' in session and session['oauth_flow'] == 'google':
        # Extract the authorization code from the request
        auth_code = request.form.get('code')
        redirect_uri = request.form.get('redirect_uri')

        google = current_app.config['GOOGLE_OAUTH_CLIENT']
        try:
            # Exchange the authorization code for an access token
            token = google.fetch_token(
                authorization_response=request.url,
                auth_code=auth_code,
                redirect_uri=redirect_uri
            )
            # Log the token for debugging
            print(f"Google access token: {token}")
            session.pop('oauth_flow', None)  # Clear the OAuth flow from the session
            return jsonify({'success': True, 'token': token}), 200
        except Exception as e:
            print(f"Error exchanging token: {e}")
            return jsonify({'error': 'Failed to exchange token'}), 400
    else:
        # Existing custom OAuth flow
        response = authorization.create_token_response()
        response_data = response.get_data(as_text=True)
        json_data = json.loads(response_data)
        access_token = json_data.get('access_token', None)
        if access_token is not None:
            save_token_to_file(access_token)
        return response


# start: google oauth
@bp.route('/google/login')
def google_login():
    # Store the flow type in the session to identify it later in the OAuth process
    session['oauth_flow'] = 'google'
    google = current_app.config['GOOGLE_OAUTH_CLIENT']
    # Retrieve the state intended for the custom GPT (OpenAI) from the session
    gpt_state = session.get('gpt_state')
    # redirect_uri = os.environ.get('OPENAI_REDIRECT_URI')
    redirect_uri = url_for('home.google_authorize', _external=True)
    # return google.authorize_redirect(redirect_uri, state=gpt_state)
    return google.authorize_redirect(redirect_uri)


@bp.route('/google/authorize')
def google_authorize():
    google = current_app.config['GOOGLE_OAUTH_CLIENT']
    redirect_uri = url_for('home.google_authorize', _external=True)
    token = google.authorize_access_token(redirect_uri=redirect_uri)
    user_info = google.parse_id_token(token)

    # Check if user exists, if not, create a new one
    user = User.query.filter_by(username=user_info['email']).first()
    if not user:
        user = User(username=user_info['email'])
        db.session.add(user)
        db.session.commit()

    session['id'] = user.id
    # Redirect to the originally intended URL or default to new_home if not set
    # return redirect(session.get('post_login_redirect', url_for('home.new_home')))
    # Use the stored state intended for the custom GPT (OpenAI) for the redirect
    gpt_state = session.pop('gpt_state', None)
    # Construct the redirect URL to the custom GPT, including the state
    # Redirect to the OpenAI custom GPT callback URL
    gpt_callback_url = os.environ.get('OPENAI_REDIRECT_URI')
    if gpt_state:
        gpt_callback_url = f"{gpt_callback_url}?state={gpt_state}"
    return redirect(gpt_callback_url)


# end: google oauth

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

    # Instead of checking revoked, check if the token is expired
    if not token or token.expires_in + token.issued_at < datetime.now(timezone.utc).timestamp():
        raise Unauthorized(description="Invalid or expired token.")

    # Fetch the user associated with the token
    user = User.query.get(token.user_id)
    if not user:
        raise Unauthorized(description="User not found.")

    # Proceed with token and user
    return token, user


def validate_bearer_token_1():
    google = current_app.config['GOOGLE_OAUTH_CLIENT']
    authorization = request.headers.get("Authorization", None)
    if not authorization:
        raise Unauthorized(description="Authorization header is missing.")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise Unauthorized(description="Invalid authorization header format.")

    token_value = authorization[len(prefix):]
    token = OAuth2Token.query.filter_by(access_token=token_value).first()

    if token:
        if token.expires_in + token.issued_at < datetime.now(timezone.utc).timestamp():
            raise Unauthorized(description="Invalid or expired token.")
        user = User.query.get(token.user_id)
    else:
        user_info = google.parse_id_token(token_value)
        if not user_info:
            raise Unauthorized(description="Invalid or expired token.")
        user = User.query.filter_by(username=user_info['email']).first()

    if not user:
        raise Unauthorized(description="User not found.")

    return token, user


@bp.route('/api/data')
def protected_data():
    try:
        token, user = validate_bearer_token_1()
        # Now you have the user object as well, you can use it as needed
        return jsonify({"message": "This is protected data", "user_id": user.id, "username": user.username})
    except Unauthorized as e:
        return jsonify({"error": str(e)}), 401


# This is for creating some new endpoints based on openai pet sample so that
# we have lower possibility to go wrong
# Hardcoded sample pets data
pets = [
    {"id": 1, "name": "Fido", "tag": "dog"},
    {"id": 2, "name": "Whiskers", "tag": "cat"},
    {"id": 3, "name": "Charlie", "tag": "squirrel"},
    {"id": 4, "name": "Buddy", "tag": "dog"},
]


@bp.route('/api/pets', methods=['GET'])
@detailed_logging
def listPets():
    try:
        token, user = validate_bearer_token_1()
        limit = request.args.get('limit', 100, type=int)
        # return jsonify(pets[:limit])
        return jsonify({"pets": pets[:limit], "user": {"id": user.id, "username": user.username}})
    except Unauthorized as e:
        return jsonify({"error": str(e)}), 401


@bp.route('/api/pets', methods=['POST'])
def createPets():
    # This is a simple example, in real scenarios, you would parse and save the incoming request data
    return jsonify({}), 201


@bp.route('/api/pets/<petId>', methods=['GET'])
def showPetById(petId):
    pet = next((pet for pet in pets if str(pet['id']) == petId), None)
    if pet:
        return jsonify(pet)
    else:
        return jsonify({"error": "Pet not found"}), 404
