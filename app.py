from flask import Flask, request, jsonify
import logging, argparse, time
from utils import make_post_request, make_get_request
from constants import HYDERABAD, GOA, PILANI

app = Flask(__name__)

region_servers = None
region_replica = None


@app.route('/')
def home():
    return "Welcome to LeaderBoard System!"


@app.route("/register_node", methods=["POST"])
def register_node():
    data = request.get_json()
    ip = data.get('ip')
    port = data.get('port')
    region = data.get('region')
    
    if not ip or not port or not region:
        return jsonify({'error': 'Invalid data'}), 400
    
    region_servers[region] = {
        "ip": ip,
        "port": port,
    }

    app.logger.info(f"Node registered: {region_servers[region]['ip']}:{region_servers[region]['port']}")
    return jsonify(data), 200


@app.route("/unregister_node", methods=["POST"])
def unregister_node():
    data = request.get_json()
    ip = data.get('ip')
    port = data.get('port')
    region = data.get('region')

    if not ip or not port or not region:
        return jsonify({'error': 'Invalid data'}), 400
    
    region_servers[region] = None
    app.logger.info(f"Node unregistered: {ip}:{port}")
    return jsonify(data), 200


@app.route("/post_score", methods=["POST"])
def post_score():
    data = request.get_json()
    player_id = data.get("player_id")
    player_name = data.get("player_name")
    score = data.get("score")
    region = data.get("region")
    timestamp = str(time.time())
    
    if not all([player_id, player_name, score]):
        return jsonify({"error": "Invalid data"}), 400

    region_server_info = region_servers[region]
    region_server_replica_info = region_servers[region_replica[region]]

    if not region_server_info and not region_server_replica_info:
        return jsonify({"error": "Failed to store data"}), 500

    processed_data = {
        "key": player_id,
        "value": {
            "player_name": player_name,
            "player_id": player_id,
            "score": score,
            "timestamp": timestamp,
            "region": region
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
        results.append(make_post_request(node_addr, processed_data, app.logger))

    for result in results:
        if result["status_code"] not in [200, 201]:
            app.logger.error(f"Error storing data at {result['url']}: {result['response']}")
            return jsonify({'error': f"Failed to store data at {result['url']}"}, result['status_code']), 500

    return jsonify({'message': "Data stored successfully"}), 200


@app.route("/get_scores", methods=["GET"])
def get_scores():
    scores = {}
    region = request.args.get('region')

    for r in [HYDERABAD, GOA, PILANI]:
        if not region or (region == r): 
            region_server_info = region_servers[r]
            region_server_replica_info = region_servers[region_replica[r]]

            region_scores = {}

            if region_server_info:
                url_prime_region = f"http://{region_server_info.get('ip')}:{region_server_info.get('port')}/get_region_data"
                response = make_get_request(url_prime_region, params={
                    "region":r
                }, logger = app.logger)
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if len(region_scores) == 0 and region_server_replica_info:
                url_prime_region = f"http://{region_server_replica_info.get('ip')}:{region_server_replica_info.get('port')}/get_region_data"
                response = make_get_request(url_prime_region, params={
                    "region":r,
                    "isReplica": "True"
                }, logger = app.logger)
                if response["status_code"] in [200, 201]:
                    region_scores.update(response["response"])

            if region_scores == {}:
                continue
            else:
                scores.update(region_scores)
    
    return jsonify(scores), 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Master Server')
    parser.add_argument('--port', type=int, required=True, help='Port for the Master Server')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')

    args = parser.parse_args()
    PORT = args.port
    MASTER_SERVER_HOST = args.master_server_host

    logging.basicConfig(level=logging.INFO)
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

    app.run(debug=True, port=PORT, host=MASTER_SERVER_HOST)
