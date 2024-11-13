from flask import Flask, request, jsonify
import logging, atexit, argparse
from db_operations import write, get_data
from node_utils import make_post_request

app = Flask(__name__)
region = None
other_region = None
HOST = None
PORT = None



def register_with_master(master_server_url):
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{master_server_url}/register_node"
    response = make_post_request(url, data, app.logger)
    
    if response['status_code'] == 200:
        app.logger.info('Registered with master server successfully.')
    else:
        app.logger.error('Failed to register with master server: %s', response['response'])


def unregister_with_master(master_server_url):
    data = {
        'ip': HOST,
        'port': str(PORT),
        'region': region
    }
    url = f"{master_server_url}/unregister_node"
    response = make_post_request(url, data)
    
    if response['status_code'] == 200:
        app.logger.info('Unregistered with master server successfully.')
    else:
        app.logger.error('Failed to unregister with master server: %s', response['response'])


@app.route("/store_score", methods=["POST"])
def store_data():
    data = request.get_json()
    if not data or not data.get("key") or not data.get("value"):
        return jsonify({"message": "Invalid Data"}), 400
    
  
    value = data.get("value")  
    if value.get("region") not in [region, other_region]:
        return jsonify({"error": "Invalid Node to store the data"}), 500
    
    num_of_failed_put_opt = 0

    if region == value.get("region"):
        try:
            write(region, data, app.logger)
        except Exception as e:
            app.logger.error(f"Error during put operation: {e}")
            num_of_failed_put_opt += 1

    elif other_region == value.get("region"):
        try:
            write(f"{other_region}_other", data, app.logger)
        except Exception as e:
            app.logger.error(f"Error during put operation: {e}")
            num_of_failed_put_opt += 1

    if num_of_failed_put_opt == 2:
        return jsonify({"error": "Cannot store the data"}), 500
    
    return jsonify({'message': "Stored Successfully"}), 200


@app.route('/get_region_data', methods=['GET'])
def get_region_data():
    region = request.args.get('region')
    other = '_other' if request.args.get('isReplica') == 'True' else ''
    data = get_data(f"{region}{other}", app.logger)
    return jsonify(data), 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Node Server')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Node server host')
    parser.add_argument('--port', type=int, required=True, help='Port for the Node Server')
    parser.add_argument('--region', type=str, required=True, help='Data from the region to store')
    parser.add_argument('--other_region', type=str, required=True, help='Data from the other region to store')
    parser.add_argument('--master_server_host', type=str, default='127.0.0.1', help='Master server host')
    parser.add_argument('--master_server_port', type=str, default='8080', help='Port for Master server')

    args = parser.parse_args()
    PORT = args.port
    HOST = args.host
    MASTER_SERVER_HOST = args.master_server_host
    MASTER_SERVER_PORT = args.master_server_port
    region = args.region
    other_region = args.other_region

    logging.basicConfig(level=logging.INFO)
    MASTER_SERVER_URL = f"http://{MASTER_SERVER_HOST}:{MASTER_SERVER_PORT}"
    register_with_master(MASTER_SERVER_URL)
    atexit.register(unregister_with_master, MASTER_SERVER_URL)

    app.run(debug=True, port=PORT, host=HOST, use_reloader=False)