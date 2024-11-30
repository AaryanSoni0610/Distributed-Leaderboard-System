from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from multiprocessing import Process
import argparse, time, uvicorn
from connections import *
from db_ops import *

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

class ScoreData(BaseModel):
    player_id: str
    player_name: str
    score: int
    timestamp: float
    region: str

@app.get("/get_region_data_master")
def get_all_regions():
    return get_regions()

@app.get("/")
def home():
    return "Welcome to LeaderBoard System!"

def heartbeat():
    while True:
        time.sleep(60)
        print("Heartbeat")
        regions = get_all_regions()
        results = []
        for region in regions:
            if region[-1] == 1:
                results.append(make_post_request(f'http://{region[1]}:{region[2]}/are-you-active', {}))
        
        for i in range(len(results)):
            if results[i]["status_code"] != 200:
                print(f"Region {regions[i][3]} is not active")
                unregister_node(Node(ip=regions[i][1], port=regions[i][2], region=regions[i][3]))

def sync_data(prev_id, curr_ip, curr_port, isReplica='True'):
    prev_region, prev_ip, prev_port, prev_active = get_region_details(prev_id)
    if not prev_active:
        print(f"Region {prev_region} is not active")
        return
    results = make_get_request(f'http://{prev_ip}:{prev_port}/get_region_data', params={"region": prev_region})
    score = results["response"]['scores']
    
    if not score:
        print(f"No data to sync from {prev_region}")
        return
    
    region_wise_scores = []
    
    scores = []
    for s in score:
        scores += [ScoreData(**s)]
        
    for s in scores:
        region_wise_scores +=[
            {
                "key": s.player_id,
                "value": {
                    "player_name": s.player_name,
                    "player_id": s.player_id,
                    "score": s.score,
                    "timestamp": s.timestamp,
                    "region": s.region
                }
            }
        ]

    results = []
    
    time.sleep(1)
    results.append(make_post_request(f'http://{curr_ip}:{curr_port}/store_score', {prev_region:region_wise_scores, 'isReplica': isReplica}))
    
    for result in results:
        if result["status_code"] not in [200, 201]:
            print(f"Failed to store data at {result['url']}")

@app.post("/register_node")
def register_node(node: Node):
    if not node.ip or not node.port or not node.region:
        print('Invalid data to register')
        return
    
    only_update = add_region(node.ip, node.port, node.region)
    total_regions = update_replication_destinations()
    
    if total_regions > 2 and not only_update:
        print(1)
        next_region, next_ip, next_port, next_active = get_region_details(1)
        prev_region, prev_ip, prev_port, prev_active = get_region_details(total_regions-1)
        
        result = make_post_request(f'http://{next_ip}:{next_port}/delete_replica', {"region": prev_region, "isReplica": "True"})
        if result["status_code"] not in [200, 201]:
            print(f"Failed to delete replica {prev_region}")
        
        sync_data(total_regions-1, node.ip, node.port)
        time.sleep(1)
    
    elif total_regions > 2 and only_update:
        print(2)
        curr_id, curr_ip, curr_port, active = get_region_details(node.region)
        
        regions = get_regions()
        total_regions = len(regions)

        prev_id = curr_id - 1 if curr_id > 1 else total_regions
        next_id = curr_id + 1 if curr_id < total_regions else 1

        is_prev_active = None
        is_next_active = None
        for r in regions:
            if r[0] == prev_id and prev_id != curr_id:
                prev_region = r[3]
                is_prev_active = r[-1]
            if r[0] == next_id and next_id != curr_id:
                next_region = r[3]
                is_next_active = r[-1]
                next_ip = r[1]
                next_port = r[2]
        
        if is_prev_active:
            replication_dest, is_active = get_temp_replication_dest(prev_id)
            if is_active:
                results = make_post_request(f'{replication_dest}/delete_replica', {"region": prev_region, "isReplica": "Temp"})
                if results["status_code"] not in [200, 201]:
                    print(f"Failed to fetch data from temp replica of {node.region}")
                else:
                    update_temp_replication_dest(prev_id, 0)
        
            sync_data(prev_id, curr_ip, curr_port)
            time.sleep(1)
        
        if is_next_active:
            sync_data(curr_id, next_ip, next_port)
        
    elif total_regions > 1 and not only_update:
        print(3)
        sync_data(total_regions - 1, node.ip, node.port)

    elif only_update:
        print(4)
        curr_id, curr_ip, curr_port, active = get_region_details(node.region)
        
        regions = get_regions()
        total_regions = len(regions)
        prev_id = curr_id - 1 if curr_id > 1 else total_regions
        print('prev_id',prev_id)
        for r in regions:
            if r[0] == prev_id:
                prev_region = r[3]
                is_prev_active = r[-1]
                break
        
        if is_prev_active:
            replication_dest, is_active = get_temp_replication_dest(prev_id)
            if is_active:
                print('Removing temp replica of', prev_region, 'from', replication_dest)
                results = make_post_request(f'{replication_dest}/delete_replica', {"region": prev_region, "isReplica": "Temp"})
                if results["status_code"] not in [200, 201]:
                    print(f"Failed to fetch data from temp replica of {node.region}")
                else:
                    update_temp_replication_dest(curr_id, 0)
            
            sync_data(prev_id, curr_ip, curr_port)

@app.post("/unregister_node")
def unregister_node(node: Node):
    if not node.ip or not node.port or not node.region:
        print('Invalid data to unregister')
        return
    
    print(f"Unregistering node {node.region}")
    prev_reg_id, next_region_id = remove_region(node.region)
    
    print('prev_reg_id', prev_reg_id)
    print('next_region_id', next_region_id)
    
    if prev_reg_id !=0 and next_region_id != 0:
        next_region, next_ip, next_port, active = get_region_details(next_region_id)
        sync_data(prev_reg_id, next_ip, next_port, 'Temp')

@app.get('/all-available-nodes')
def all_available_nodes():
    regions = get_regions()
    region_names = [r[3] for r in regions]
    return region_names

@app.post("/post_score")
def post_score(score: dict):
    print(score)
    timestamp = str(time.time())
    
    regions = get_all_regions()
    total_regions = len(regions)
    
    region_servers = {}
    region_replica = {}
    region_wise_scores = {}
    node_address = {}
    is_temp_replica = {}
    is_active = {}
    
    for r in regions:
        is_active[r[3]] = r[-1]
        region_servers[r[3]] = f'http://{r[1]}:{r[2]}'
        region_wise_scores[r[3]] = {r[3]:[]}
        if total_regions > 1:
            region_replica[r[3]], is_temp_replica[r[3]] = get_replication_dest(r[0], total_regions)
            node_address[r[3]] = (region_servers[r[3]]+'/store_score', region_replica[r[3]]+'/store_score')
        else:
            node_address[r[3]] = (region_servers[r[3]]+'/store_score')
    
    scores=[]
    for s in score['scores']:
        scores+=[Score(**s)]

    for s in scores:
        try:
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
        except KeyError:
            pass

    results = []
    
    for reg in region_wise_scores.keys():
        if region_wise_scores[reg][reg] and is_active[reg] == 1:
            if total_regions == 1:
                results.append(make_post_request(node_address[reg], {reg:region_wise_scores[reg][reg], 'isReplica': None}))
            else:
                results.append(make_post_request(node_address[reg][0], {reg:region_wise_scores[reg][reg], 'isReplica': None}))
                isReplica = 'True'
                if is_temp_replica[reg]:
                    isReplica = 'Temp'
                results.append(make_post_request(node_address[reg][1], {reg:region_wise_scores[reg][reg], 'isReplica': isReplica}))
        elif is_active[reg] == 0:
            print(f"Region {reg}'s main server is not active, cannot store the data to this region")
    
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
        nodes_address = [f"{nodes_address[0]}/get_region_data", f"{nodes_address[1]}/get_region_data"]

        params = [{"region": region}, {"region": region, "isReplica": "True"}]
        if is_temp_replica[region]:
            params[1]["isReplica"] = 'Temp'
        
        results = []
        
        if check_if_region_active(region_id):
            results.append(make_get_request(nodes_address[0], params=params[0]))
        elif check_if_region_active(replication_dest_id):
            results.append(make_get_request(nodes_address[1], params=params[1]))
        else:
            print(f"No active nodes to fetch data for {region}")
            return scores
        
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
        
        for result in results:
            if result["status_code"] == 200:
                scores['scores'] += result["response"]['scores']
            else:
                print(f"Failed to fetch data for {result['url']}")
        
        scores['scores'] = sorted(scores['scores'], key=lambda x: x.get("score"), reverse=True)
        
    return scores

if __name__ == "__main__":
    initialize_db()
    
    parser = argparse.ArgumentParser(description='Master Server')
    parser.add_argument('--port', type=int, default=8080, help='Port for the Master Server')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Master server host')
    
    args = parser.parse_args()
    PORT = args.port
    MASTER_SERVER_HOST = args.host
    
    p = Process(target=heartbeat)
    p.start()

    uvicorn.run(app, host=MASTER_SERVER_HOST, port=PORT)