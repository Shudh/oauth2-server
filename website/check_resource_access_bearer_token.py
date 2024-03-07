import requests

# Replace with your actual URL and token
PROTECTED_RESOURCE_URL = 'https://oauth2-server-production.up.railway.app/api/data'
ACCESS_TOKEN = 'iQEpDm0qEVC68KPf7CizHPiiayak22VP5U9yM7ZSY4'


def access_protected_resource(token, url):
    """Send a GET request to access a protected resource."""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)

    # Check if the response is successful
    if response.ok:
        try:
            data = response.json()
            return data
        except ValueError:
            print('Failed to decode JSON from response.')
            return None
    else:
        print(f'Request failed: {response.status_code}')
        try:
            error_data = response.json()
            print(f'Error: {error_data}')
        except ValueError:
            print('Failed to decode JSON from error response.')
        return None


response_data = access_protected_resource(ACCESS_TOKEN, PROTECTED_RESOURCE_URL)
if response_data:
    print('Protected Resource Response:', response_data)
else:
    print('Failed to access protected resource.')
