from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import atexit, argparse, uvicorn, requests
from db_operations import *
from connections import *
from multiprocessing import Process

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

def check_replica_type(isReplica):
    if isReplica == "True":
        other = '_replica'
    elif isReplica == "Temp":
        other = '_temp'
    else:
        other = ''
    return other

@app.post('/create_replica')
async def create_replica(data: dict):
    region = data['region']
    other = check_replica_type(data['isReplica'])
    
    scores = [ScoreData(**s) for s in data['scores']]
    write(f"{region}{other}", scores)
    
    return {"message": "Replica created successfully"}

@app.post('/delete_replica')
async def delete_replica(data: dict):
    region = data['region']
    other = check_replica_type(data['isReplica'])
        
    delete_database(f"{region}{other}")
    return {"message": "Replica deleted successfully"}

@app.post("/store_score")
async def store_data(data: dict):
    isReplica = data['isReplica']
    del data['isReplica']
    
    other = check_replica_type(isReplica)
    
    key = list(data.keys())[0]
    scores = [ScoreData(**s) for s in data[key]]
    
    replication_region = key
    
    num_of_failed_put_opt = 0

    if current_region == key:
        try:
            write(region, scores)
        except Exception as e:
            num_of_failed_put_opt += 1

    else:
        try:
            write(f"{key}{other}", scores)
        except Exception as e:
            num_of_failed_put_opt += 1

    if num_of_failed_put_opt == 2:
        print("Failed to store data in both regions")
    
    return {"message": "Stored Successfully"}

@app.get('/get_region_data')
async def get_region_data(region: str, isReplica: str = None):
    other = check_replica_type(isReplica)
    
    data = get_data(f"{region}{other}")
    return data

@app.post('/sync_data')
async def sync_data(region: str, data: dict = None):
    data = get_data(f"{region}_replica")

@app.get('')
def home():
    return {"message": "Node Server"}

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
    current_region = region

    write(region, [])
    
    MASTER_SERVER_URL = f"http://{MASTER_SERVER_HOST}:{MASTER_SERVER_PORT}"
    p = Process(target=register_with_master, args=(HOST, PORT, region, MASTER_SERVER_URL))
    p.start()
    atexit.register(lambda: unregister_with_master(HOST, PORT, region, MASTER_SERVER_URL))

    uvicorn.run(app, host=HOST, port=PORT)