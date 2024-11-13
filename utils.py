import requests

def make_post_request(url, data, logger=None):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return {
            'url': url, 
            'status_code': response.status_code, 
            'response': response.json() if response.status_code == 200 else response.text
        }
    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"Error making POST request to {url}: {e}")
        return {
            'url': url,
            'status_code': None,
            'response': str(e)
        }


def make_get_request(url, params=None, logger=None):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return {
            'url': url,
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 200 else response.text
        }
    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"Error making GET request to {url}: {e}")
        return {
            'url': url,
            'status_code': None,
            'response': str(e)
        }