# Description: This file contains the FastAPI server that will be used to serve the model and the web interface.

from fastapi import FastAPI, UploadFile, File
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

