import requests

# Configuration for the OAuth2 server
AUTH_SERVER_BASE_URL = 'https://oauth2-server-production.up.railway.app/'
CLIENT_ID = 'kxddvuK9kySSb4BWIBFj1kqJ'
CLIENT_SECRET = '5irdHLBBFyIw52oMAUbleXBnR9By7KZwanM28HqxX9LiGJQY'
REDIRECT_URI = 'http://localhost'


def exchange_code_for_token(code):
    token_url = f"{AUTH_SERVER_BASE_URL}/oauth/token"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(token_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    return response.json()


if __name__ == "__main__":
    # Replace 'YOUR_AUTHORIZATION_CODE' with the actual authorization code you received
    authorization_code = input("Enter the authorization code: ")
    token_response = exchange_code_for_token(authorization_code)
    print("Access Token Response:")
    print(token_response)
