import sqlite3

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
            temp_replication_dest_id INTEGER DEFAULT 0,
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
    only_update = False
    if check_if_region_present(region):
        cursor.execute('UPDATE regions SET active = 1, ip = ?, port = ? WHERE region = ?', (ip, port, region))
        only_update = True
    else:
        cursor.execute('INSERT INTO regions (ip, port, region) VALUES (?, ?, ?)', (ip, port, region))
    
    conn.commit()
    conn.close()
    return only_update

def update_replication_dest(region, replication_dest_id):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE regions SET replication_dest_id = ? WHERE region = ?', (replication_dest_id, region))
    conn.commit()
    conn.close()

def get_region_details(region: str | int):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    if isinstance(region, str):
        cursor.execute('SELECT id, ip, port FROM regions WHERE region = ?', (region,))
    else:
        cursor.execute('SELECT region, ip, port FROM regions WHERE id = ?', (region,))
    region_details = cursor.fetchone()
    conn.close()
    return region_details

def update_replication_destinations():
    regions = get_regions()
    num_regions = len(regions)
    for i in range(num_regions):
        current_region = regions[i][3]
        next_region_id = ((i+1) % num_regions) + 1
        
        update_replication_dest(current_region, next_region_id)
    return num_regions

def check_if_region_active(region_id):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    cursor.execute('SELECT active FROM regions WHERE id = ?', (region_id,))
    region_data = cursor.fetchone()
    conn.close()
    if region_data[0] == 1:
        return True
    return False

def get_regions():
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
        # return ip and port of next region + is_temp_replica = 0
        return f'http://{ip}:{port}', 0
    else:
        cursor.execute('SELECT temp_replication_dest_id FROM regions WHERE id = ?', (region_id,))
        temp_replication_dest_id = cursor.fetchone()[0]
        ip, port = cursor.execute('SELECT ip, port FROM regions WHERE id = ?', (temp_replication_dest_id,)).fetchone()
        conn.close()
        # return ip and port of temp replica region + is_temp_replica = 1
        return f'http://{ip}:{port}', 1

def remove_region(region):
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE regions SET active = 0 WHERE region = ?', (region,))
    conn.commit()
    
    cursor.execute('SELECT id FROM regions')
    total_regions = len(cursor.fetchall())
    
    if total_regions == 1:
        conn.close()
        return 0, 0
    
    cursor.execute('SELECT id FROM regions WHERE region = ?', (region, ))
    curr_reg_id = cursor.fetchone()[0]
    print('Curr',curr_reg_id)

    cursor.execute('SELECT id FROM regions WHERE replication_dest_id = ?', (curr_reg_id,))
    prev_reg_id = cursor.fetchone()[0]
    print('Prev',prev_reg_id)
    
    cursor.execute('SELECT active FROM regions WHERE id = ?', (prev_reg_id,))
    prev_reg_active = cursor.fetchone()[0]
    print('Act', prev_reg_active)
    if prev_reg_active == 0:
        cursor.execute('SELECT id FROM regions WHERE temp_replication_dest_id = ?', (curr_reg_id,))
        prev_reg_id = cursor.fetchone()[0]
        print('Temp', prev_reg_id)
    
    cursor.execute('SELECT id FROM regions WHERE active = 1')
    all_active_nodes = cursor.fetchall()
    
    next_reg_id = 0
    if  all_active_nodes:
        for node in all_active_nodes:
            if curr_reg_id < node[0]:
                next_reg_id = node[0]
                print('Next', next_reg_id)
                break
        else:
            next_reg_id = all_active_nodes[0][0]
            print('Next', next_reg_id)
    
    cursor.execute('UPDATE regions SET temp_replication_dest_id = ? WHERE id = ?', (next_reg_id, prev_reg_id))
    
    conn.commit()
    conn.close()
    return prev_reg_id, next_reg_id
