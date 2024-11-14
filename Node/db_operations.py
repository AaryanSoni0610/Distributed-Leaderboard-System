import json, plyvel

def get_data(region, logger):
    data = {}
    try:
        with plyvel.DB(f'{region}_db', create_if_missing=False) as db:
            snapshot = db.snapshot()
            with snapshot.iterator() as it:
                for key, value in it:
                    decoded_value = json.loads(value.decode('utf-8'))
                    data[key.decode('utf-8')] = decoded_value
    except Exception:
        logger.error(f"{region}_db doesnot exit")
        
    return data


def write(region, data, logger):
    key = data.get("key")
    value = data.get("value")
    with plyvel.DB(f'{region}_db', create_if_missing=True) as db:
        db.put(key.encode('utf-8'), json.dumps(value).encode('utf-8'))
        if logger:
            logger.info(f"Put operation successful for key {key} in {region}_db")

