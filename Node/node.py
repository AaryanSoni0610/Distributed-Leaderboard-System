from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import atexit, argparse, uvicorn, requests
from db_operations import write, get_data

app = FastAPI()
region = None
HOST = None
PORT = None
MASTER_SERVER_URL = None

class NodeData(BaseModel):
    ip: str
    port: str
    region: str

class ScoreData(BaseModel):
    key: str
    value: dict

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

def register_with_master():
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{MASTER_SERVER_URL}/register_node"
    response = make_post_request(url, data)
    
    if response['status_code'] != 200:
        raise HTTPException(status_code=500, detail='Failed to register with master server')

def unregister_with_master():
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{MASTER_SERVER_URL}/unregister_node"
    response = make_post_request(url, data)
    
    if response['status_code'] != 200:
        raise HTTPException(status_code=500, detail='Failed to unregister with master server')

@app.post("/store_score")
async def store_data(data: dict):
    key = list(data.keys())[0]
    scores = [ScoreData(**s) for s in data[key]]
    
    replication_region = key
    
    num_of_failed_put_opt = 0

    if region == key:
        try:
            write(region, scores)
        except Exception as e:
            print(e)
            num_of_failed_put_opt += 1

    else:
        try:
            write(f"{replication_region}_replica", scores)
        except Exception as e:
            print(e)
            num_of_failed_put_opt += 1

    if num_of_failed_put_opt == 2:
        raise HTTPException(status_code=500, detail="Cannot store the data")
    
    return {"message": "Stored Successfully"}

@app.get('/get_region_data')
async def get_region_data(region: str, isReplica: str = None, isTempReplica: str = None):
    other = '_replica' if isReplica else ''
    data = get_data(f"{region}{other}")
    return data

@app.post('/sync_data')
async def sync_data(region: str, isReplica: str = None, data: dict = None):
    data = get_data(f"{region}_replica")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Node Server')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Node server host')
    parser.add_argument('--port', type=int, required=True, help='Port for the Node Server')
    parser.add_argument('--region', type=str, required=True, help='Data from the region to store')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')
    parser.add_argument('--master_server_port', type=str, default='8080', help='Port for Master server')

    args = parser.parse_args()
    PORT = args.port
    HOST = args.host
    MASTER_SERVER_HOST = args.master_server_host
    MASTER_SERVER_PORT = args.master_server_port
    region = args.region

    MASTER_SERVER_URL = f"http://{MASTER_SERVER_HOST}:{MASTER_SERVER_PORT}"
    register_with_master()
    atexit.register(unregister_with_master)

    uvicorn.run(app, host=HOST, port=PORT)