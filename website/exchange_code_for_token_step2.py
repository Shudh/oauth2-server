import requests
from urllib.parse import urljoin

# Configuration for the OAuth2 server
AUTH_SERVER_BASE_URL = 'https://oauth2-server-production.up.railway.app/'
CLIENT_ID = 'kxddvuK9kySSb4BWIBFj1kqJ'
CLIENT_SECRET = '5irdHLBBFyIw52oMAUbleXBnR9By7KZwanM28HqxX9LiGJQY'
REDIRECT_URI = 'http://localhost'  # This must match the redirect URI used for obtaining the code

# Token endpoint
token_url = urljoin(AUTH_SERVER_BASE_URL, 'oauth/token')


def exchange_code_for_token(code):
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(token_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    return response.json()


def main():
    # Replace 'your_code_here' with the actual code you received
    # iAfILouHJM0iV6D8lddFR6twpM1RPl0B5RuO3OkxlZWXOPSX
    code = "96IY70vp0exwsgUlxCfOzLrD3KEBbAb1JVqpPnaHfVYnfZGo"
    token_response = exchange_code_for_token(code)
    print("Access Token Response:")
    print(token_response)


if __name__ == '__main__':
    main()
