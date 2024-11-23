from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from multiprocessing import Process
import argparse, time, uvicorn, sqlite3, requests, time

region_servers = None
region_replica = None

app = FastAPI()

class Node(BaseModel):
    ip: str
    port: int
    region: str

class Score(BaseModel):
    player_id: str
    player_name: str
    score: int
    region: str

def make_post_request(url, data):
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
        return {
            'url': url,
            'status_code': None,
            'response': str(e)
        }

def make_get_request(url, params=None):
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
        return {
            'url': url,
            'status_code': None,
            'response': str(e)
        }

def initialize_db():
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            region TEXT UNIQUE NOT NULL,
            replication_dest_id INTEGER DEFAULT 0,
            temp_replication_dest_id TEXT DEFAULT 0,
            active INT DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def check_if_region_present(region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('SELECT region FROM regions WHERE region = ?', (region,))
    region_data = cursor.fetchone()
    conn.close()
    if region_data:
        return True
    return False

def add_region(ip, port, region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    if check_if_region_present(region):
        cursor.execute('UPDATE regions SET active = 1 WHERE region = ?', (region,))
    else:
        cursor.execute('INSERT INTO regions (ip, port, region) VALUES (?, ?, ?)', (ip, port, region))
    conn.commit()
    conn.close()

def update_replication_dest(region, replication_dest_id):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE regions SET replication_dest_id = ? WHERE region = ?', (replication_dest_id, region))
    conn.commit()
    conn.close()

def update_replication_destinations():
    regions = get_all_regions()
    num_regions = len(regions)
    for i in range(num_regions):
        current_region = regions[i][3]
        next_region_id = ((i+1) % num_regions) + 1
        
        update_replication_dest(current_region, next_region_id)

def check_if_region_active(region_id):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('SELECT active FROM regions WHERE id = ?', (region_id,))
    region_data = cursor.fetchone()
    conn.close()
    if region_data[0] == 1:
        return True
    return False

@app.get("/get_region_data_master")
def get_all_regions():
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM regions')
    regions = cursor.fetchall()
    conn.close()
    return regions

def get_replication_dest(region_id: int, total_regions: int):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    
    next_region_id = (region_id % total_regions) + 1
    cursor.execute('SELECT ip, port, active FROM regions WHERE id = ?', (next_region_id,))
    ip, port,active = cursor.fetchone()
    
    if active == 1:
        conn.close()
        return f'http://{ip}:{port}', 0
    else:
        cursor.execute('SELECT temp_replication_dest_id FROM regions WHERE id = ?', (region_id,))
        temp_replication_dest_id = cursor.fetchone()[0]
        ip, port = cursor.execute('SELECT ip, port FROM regions WHERE id = ?', (temp_replication_dest_id,)).fetchone()
        conn.close()
        return f'http://{ip}:{port}', 1

def remove_region(region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    print('Region',region,'deactivated')
    cursor.execute('UPDATE regions SET active = 0 WHERE region = ?', (region,))
    conn.commit()
    conn.close()

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
def post_score(score: dict):
    timestamp = str(time.time())
    
    regions = get_all_regions()
    total_regions = len(regions)
    region_servers = {}
    region_replica = {}
    region_wise_scores = {}
    node_address = {}
    is_temp_replica = {}
    for r in regions:
        region_servers[r[3]] = f'http://{r[1]}:{r[2]}'
        region_replica[r[3]], is_temp_replica[r[3]] = get_replication_dest(r[0], total_regions)
        region_wise_scores[r[3]] = {r[3]:[]}
        node_address[r[3]] = (region_servers[r[3]]+'/store_score', region_replica[r[3]]+'/store_score')
    
    scores=[]
    for s in score['scores']:
        scores+=[Score(**s)]

    for s in scores:
        region_wise_scores[s.region][s.region]+=[
            {
                "key": s.player_id,
                "value": {
                    "player_name": s.player_name,
                    "player_id": s.player_id,
                    "score": s.score,
                    "timestamp": timestamp,
                    "region": s.region
                }
            }
        ]

    results = []
    
    for reg in region_wise_scores.keys():
        if region_wise_scores[reg][reg]:
            results.append(make_post_request(node_address[reg][0], region_wise_scores[reg]))
            results.append(make_post_request(node_address[reg][1], region_wise_scores[reg]))
    
    for result in results:
        if result["status_code"] not in [200, 201]:
            print(f"Failed to store data at {result['url']}")

    return {"message": "Data stored successfully"}

@app.get("/get_scores")
def get_scores(region: str = None):
    scores = {'scores': []}

    regions = get_all_regions()
    total_regions = len(regions)
    region_servers = {}
    region_replica = {}
    is_temp_replica = {}
    for r in regions:
        region_servers[r[3]] = f'http://{r[1]}:{r[2]}'
        region_replica[r[3]], is_temp_replica[r[3]] = get_replication_dest(r[0], total_regions)

    if region:
        region_id = [r[0] for r in regions if r[3] == region][0]
        replication_dest_id = [r[4] for r in regions if r[3] == region][0]
        nodes_address = [region_servers[region], region_replica[region]]
        nodes_address = [f"{nodes_address[0]}/get_region_data"]

        params = [{"region": region}, {"region": region, "isReplica": "True", "isTempReplica": ""}]
        if is_temp_replica[region]:
            params[1]["isReplica"] = ''
            params[1]["isTempReplica"] = "True"
        
        results = []
        
        if check_if_region_active(region_id):
            results.append(make_get_request(nodes_address[0], params=params[0]))
        elif check_if_region_active(replication_dest_id):
            results.append(make_get_request(nodes_address[1], params=params[1]))
        else:
            print(f"No active nodes to fetch data for {region}")
        
        print(results[0])
        if results[0]["status_code"] == 200:
            scores['scores'] = results[0]["response"]['scores']
        else:
            print(f"Failed to fetch data for {region}")
        
    else:
        region_addresses = [f'{region_server}/get_region_data' for region_server in region_servers.values()]
        replication_addresses = [f'{region_replica}/get_region_data' for region_replica in region_replica.values()]
        
        results = []
        for i in range(len(region_addresses)):
            if check_if_region_active(regions[i][0]):
                results.append(make_get_request(region_addresses[i], params={"region": regions[i][3]}))
            elif check_if_region_active(regions[i][4]):
                results.append(make_get_request(replication_addresses[i], params={"region": regions[i][3], "isReplica": "True"}))
            else:
                print(f"No active nodes to fetch data for {regions[i][3]}")
        
        print(results[0]["response"]['scores'])
        for result in results:
            if result["status_code"] == 200:
                scores['scores'] += result["response"]['scores']
            else:
                print(f"Failed to fetch data for {result['url']}")
        
        scores['scores'] = sorted(scores['scores'], key=lambda x: x.get("score"), reverse=True)
        print(scores)
        
    return scores

if __name__ == "__main__":
    initialize_db()
    
    parser = argparse.ArgumentParser(description='Master Server')
    parser.add_argument('--port', type=int, default=8080, help='Port for the Master Server')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')
    
    args = parser.parse_args()
    PORT = args.port
    MASTER_SERVER_HOST = args.master_server_host

    uvicorn.run(app, host=MASTER_SERVER_HOST, port=PORT)