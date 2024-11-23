import json, plyvel

def get_data(region):
    data= {'scores': []}
    try:
        with plyvel.DB(f'{region}_db', create_if_missing=False) as db:
            snapshot = db.snapshot()
            with snapshot.iterator() as it:
                for key, value in it:
                    decoded_value = json.loads(value.decode('utf-8'))
                    data['scores'] += [decoded_value]
        
        # sort data based on score
        data['scores'] = sorted(data['scores'], key=lambda x: x.get("value").get("score"), reverse=True)
    except Exception:
        print(f"Error while reading data from {region}_db")
        
    return data

def write(region, data):
    with plyvel.DB(f'{region}_db', create_if_missing=True) as db:
        with db.write_batch() as wb:
            for item in data:
                item = item.dict()
                key = item.get("key")
                value = item.get("value")
                wb.put(key.encode('utf-8'), json.dumps(value).encode('utf-8'))