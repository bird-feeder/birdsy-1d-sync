import os
import sys
import subprocess

from dotenv import load_dotenv
from flask import Flask, request, json
from loguru import logger

app = Flask(__name__)

@app.route('/')
def _root():
    return 'Birdfeeder Webhooks'

@app.route('/github_push', methods=['POST', 'GET'])
def github_push():
    data = request.json
    subprocess.Popen(['/root/.pyenv/versions/py3.10/bin/python', 'app.py'])
    return data

if __name__ == '__main__':
    load_dotenv()
    logger.add('logs.log')
    app.run(host=os.environ['HOST'], port=int(os.environ['PORT']))
