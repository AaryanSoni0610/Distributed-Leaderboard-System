from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import argparse, time, uvicorn
from utils import make_post_request, make_get_request
from constants import HYDERABAD, GOA, PILANI

app = FastAPI()

region_servers = None
region_replica = None

class Node(BaseModel):
    ip: str
    port: int
    region: str

class Score(BaseModel):
    player_id: str
    player_name: str
    score: int
    region: str

@app.get("/")
def home():
    return "Welcome to LeaderBoard System!"

@app.post("/register_node")
def register_node(node: Node):
    if not node.ip or not node.port or not node.region:
        raise HTTPException(status_code=400, detail="Invalid data")
    
    region_servers[node.region] = {
        "ip": node.ip,
        "port": node.port,
    }

    return node

@app.post("/unregister_node")
def unregister_node(node: Node):
    if not node.ip or not node.port or not node.region:
        raise HTTPException(status_code=400, detail="Invalid data")
    
    region_servers[node.region] = None
    return node

@app.post("/post_score")
def post_score(score: Score):
    timestamp = str(time.time())
    
    if not all([score.player_id, score.player_name, score.score]):
        raise HTTPException(status_code=400, detail="Invalid data")

    region_server_info = region_servers[score.region]
    region_server_replica_info = region_servers[region_replica[score.region]]

    if not region_server_info and not region_server_replica_info:
        raise HTTPException(status_code=500, detail="Failed to store data")

    processed_data = {
        "key": score.player_id,
        "value": {
            "player_name": score.player_name,
            "player_id": score.player_id,
            "score": score.score,
            "timestamp": timestamp,
            "region": score.region
        }
    }

    nodes_address = []
    if region_server_info:
        address = f"http://{region_server_info.get('ip')}:{region_server_info.get('port')}"
        nodes_address.append(address)

    if region_server_replica_info:
        address = f"http://{region_server_replica_info.get('ip')}:{region_server_replica_info.get('port')}"
        nodes_address.append(address)

    nodes_address = [f"{node_address}/store_score" for node_address in nodes_address]
    results = []
    
    for node_addr in nodes_address:
        results.append(make_post_request(node_addr, processed_data))
    print(1)
    
    for result in results:
        if result["status_code"] not in [200, 201]:
            raise HTTPException(status_code=500, detail=f"Failed to store data at {result['url']}")
    print(1)

    return {"message": "Data stored successfully"}

@app.get("/get_scores")
def get_scores(region: str = None):
    scores = {}

    for r in [HYDERABAD, GOA, PILANI]:
        if not region or (region == r): 
            region_server_info = region_servers[r]
            region_server_replica_info = region_servers[region_replica[r]]

            region_scores = {}

            if region_server_info:
                url_prime_region = f"http://{region_server_info.get('ip')}:{region_server_info.get('port')}/get_region_data"
                response = make_get_request(url_prime_region, params={
                    "region":r
                })
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if len(region_scores) == 0 and region_server_replica_info:
                url_prime_region = f"http://{region_server_replica_info.get('ip')}:{region_server_replica_info.get('port')}/get_region_data"
                response = make_get_request(url_prime_region, params={
                    "region":r,
                    "isReplica": "True"
                })
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if region_scores == {}:
                continue
            else:
                scores.update(region_scores)
    
    return scores

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Master Server')
    parser.add_argument('--port', type=int, required=True, help='Port for the Master Server')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')

    args = parser.parse_args()
    PORT = args.port
    MASTER_SERVER_HOST = args.master_server_host

    region_servers = {
        HYDERABAD: None,
        GOA: None,
        PILANI: None
    }

    region_replica = {
        HYDERABAD: GOA,
        GOA: PILANI,
        PILANI: HYDERABAD
    }

    uvicorn.run(app, host=MASTER_SERVER_HOST, port=PORT)