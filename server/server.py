# Description: This file contains the FastAPI server that will be used to serve the model and the web interface.

from fastapi import FastAPI
from fastapi.responses import FileResponse
import os, random, string, json, logging as log
from multiprocessing import Process

app = FastAPI()

sep = os.path.sep

# to only store logs from this files, and not from imported modules
logger = log.getLogger(__name__)
logger.setLevel(log.DEBUG)
handler = log.FileHandler(f'server{sep}logs{sep}server.log', 'w')
handler.setLevel(log.DEBUG)
formatter = log.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

regional_servers = [
    'http://192.168.200.201:8800',
    'http://192.168.200.202:8800',
    'http://192.168.200.203:8800',
]

@app.post("/create-leaderboard/")
def create_leaderboard():
    logger.info('Creating leaderboard')
    # create leaderboard
    return {"message": "Leaderboard created"}

@app.post("/create-player/")
def create_player():
    logger.info('Creating player')
    # create player
    return {"message": "Player created"}

@app.post("/update-score/")
def update_score():
    logger.info('Updating score')
    # update score
    return {"message": "Score updated"}

@app.post("/get-leaderboard/")
def get_leaderboard():
    logger.info('Getting leaderboard')
    # get leaderboard
    return {"message": "Leaderboard retrieved"}