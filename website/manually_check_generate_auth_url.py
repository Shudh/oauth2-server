import requests
from urllib.parse import urljoin

# Configuration for the OAuth2 server
AUTH_SERVER_BASE_URL = 'https://oauth2-server-production.up.railway.app/'
CLIENT_ID = 'B4nECMbDhwlIgfNmv7Z7CHyq'
REDIRECT_URI = 'https://authlib.org'  # Placeholder

# Authorization endpoint
authorize_url = urljoin(AUTH_SERVER_BASE_URL, 'oauth/authorize')


def generate_authorization_url():
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI
    }
    authorization_url = requests.Request('GET', authorize_url, params=params).prepare().url
    print("Please go to the following URL and authorize access:")
    print(authorization_url)


if __name__ == '__main__':
    generate_authorization_url()
