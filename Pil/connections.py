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

def make_get_request(url, params=None):
    try:
        response = requests.get(url, params=params)
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

def register_with_master(HOST, PORT, region, MASTER_SERVER_URL):
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{MASTER_SERVER_URL}/register_node"
    response = make_post_request(url, data)
    
    if response['status_code'] != 200:
        print('Failed to register with master server')

def unregister_with_master(HOST, PORT, region, MASTER_SERVER_URL):
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{MASTER_SERVER_URL}/unregister_node"
    response = make_post_request(url, data)
    
    if response['status_code'] != 200:
        print('Failed to unregister with master server')
