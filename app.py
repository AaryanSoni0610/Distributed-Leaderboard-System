from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import argparse, time, uvicorn, sqlite3
from utils import make_post_request, make_get_request

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

def initialize_db():
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            region TEXT NOT NULL,
            replication_dest TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_region(ip, port, region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO regions (ip, port, region) VALUES (?, ?, ?)', (ip, port, region))
    conn.commit()
    conn.close()

def update_replication_dest(region, replication_dest_ip, replication_dest_port):
    replication_dest = f"{replication_dest_ip}:{replication_dest_port}"
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE regions SET replication_dest = ? WHERE region = ?', (replication_dest, region))
    conn.commit()
    conn.close()

@app.get("/get_region_data_master")
def get_all_regions():
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM regions')
    regions = cursor.fetchall()
    conn.close()
    return regions

def remove_region(region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM regions WHERE region = ?', (region,))
    conn.commit()
    conn.close()

def update_replication_destinations():
    regions = get_all_regions()
    num_regions = len(regions)
    for i in range(num_regions):
        current_region = regions[i][3]
        next_region_ip = regions[(i + 1) % num_regions][1]
        next_region_port = regions[(i + 1) % num_regions][2]
        update_replication_dest(current_region, next_region_ip, next_region_port)

@app.get("/")
def home():
    return "Welcome to LeaderBoard System!"

@app.post("/register_node")
def register_node(node: Node):
    if not node.ip or not node.port or not node.region:
        raise HTTPException(status_code=400, detail="Invalid data")
    
    add_region(node.ip, node.port, node.region)
    update_replication_destinations()

    return node

@app.post("/unregister_node")
def unregister_node(node: Node):
    if not node.ip or not node.port or not node.region:
        raise HTTPException(status_code=400, detail="Invalid data")
    
    remove_region(node.region)
    update_replication_destinations()
    return node

@app.post("/post_score")
def post_score(score: Score):
    timestamp = str(time.time())
    
    if not all([score.player_id, score.player_name, score.score]):
        raise HTTPException(status_code=400, detail="Invalid data")

    regions = get_all_regions()
    region_servers = {region[3]: f'http://{region[1]}:{region[2]}' for region in regions}
    region_replica = {region[3]: f'http://{region[4]}' for region in regions}
    # print('region_replica:',region_replica)
    # print('region_servers:',region_servers)
    
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

    nodes_address = [region_servers[score.region], region_replica[score.region]]

    nodes_address = [f"{node_address}/store_score" for node_address in nodes_address]
    results = []
    
    # print('nodes_address:',nodes_address)
    for node_addr in nodes_address:
        results.append(make_post_request(node_addr, processed_data))
    
    # print('results:',results)
    for result in results:
        if result["status_code"] not in [200, 201]:
            raise HTTPException(status_code=500, detail=f"Failed to store data at {result['url']}")

    return {"message": "Data stored successfully"}

@app.get("/get_scores")
def get_scores(region: str = None):
    scores = {}

    regions = get_all_regions()
    region_servers = {region[3]: {"ip": region[1], "port": region[2]} for region in regions}
    region_replica = {region[3]: region[4] for region in regions}

    for r in region_servers.keys():
        if not region or (region == r): 
            region_server_info = region_servers.get(r)
            region_server_replica_info = region_replica.get(r)

            region_scores = {}

            if region_server_info:
                url_prime_region = f"http://{region_server_info.get('ip')}:{region_server_info.get('port')}/get_region_data"
                response = make_get_request(url_prime_region, params={"region": r})
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if len(region_scores) == 0 and region_server_replica_info:
                url_prime_region = f"http://{region_server_replica_info}/get_region_data"
                response = make_get_request(url_prime_region, params={"region": r, "isReplica": "True"})
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if region_scores == {}:
                continue
            else:
                scores.update(region_scores)
    
    return scores

@app.on_event("startup")
def startup_event():
    global region_servers, region_replica
    regions = get_all_regions()
    region_servers = {region[3]: {"ip": region[1], "port": region[2]} for region in regions}
    region_replica = {region[3]: region[4] for region in regions}

if __name__ == "__main__":
    initialize_db()
    parser = argparse.ArgumentParser(description='Master Server')
    parser.add_argument('--port', type=int, required=True, help='Port for the Master Server')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')
    

    args = parser.parse_args()
    PORT = args.port
    MASTER_SERVER_HOST = args.master_server_host

    uvicorn.run(app, host=MASTER_SERVER_HOST, port=PORT)