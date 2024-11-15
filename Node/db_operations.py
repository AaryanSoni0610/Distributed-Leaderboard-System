import json, plyvel

def get_data(region):
    data = {}
    try:
        with plyvel.DB(f'{region}_db', create_if_missing=False) as db:
            snapshot = db.snapshot()
            with snapshot.iterator() as it:
                for key, value in it:
                    decoded_value = json.loads(value.decode('utf-8'))
                    data[key.decode('utf-8')] = decoded_value
    except Exception:
        print(f"Error while reading data from {region}_db")
        
    return data


def write(region, data):
    key = data.get("key")
    value = data.get("value")
    with plyvel.DB(f'{region}_db', create_if_missing=True) as db:
        db.put(key.encode('utf-8'), json.dumps(value).encode('utf-8'))

