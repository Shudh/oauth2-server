import requests

# Configuration for the OAuth2 server
PROTECTED_RESOURCE_URL = 'https://oauth2-server-production.up.railway.app/api/me'


def access_protected_resource(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(PROTECTED_RESOURCE_URL, headers=headers)
    return response.json()

# Access Token Response:
# {'access_token': 'Ggniwjg3YA9jAoZfkaGOfP3TIG9Auq4CS8kFiPxOU7', 'expires_in': 864000, 'scope': 'profile', 'token_type': 'Bearer'}
if __name__ == "__main__":
    # Replace 'YOUR_ACCESS_TOKEN' with the actual access token you received
    access_token = input("Enter the access token: ")
    resource_response = access_protected_resource(access_token)
    print("Protected Resource Response:")
    print(resource_response)
