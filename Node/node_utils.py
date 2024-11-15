import requests

def make_post_request(url, data):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status() 
        return {
            'url': url, 
            'status_code': response.status_code, 
            'response': response.json() if response.status_code == 200 else response.text
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status_code': None,
            'response': str(e)
        }