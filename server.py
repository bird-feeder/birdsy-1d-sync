import os
import sys
import shlex
import subprocess
import time

import cronitor
from dotenv import load_dotenv
from flask import Flask, request, json
from loguru import logger

app = Flask(__name__)


@app.route('/')
def _root():
    return 'Birdfeeder Webhooks'


@app.route('/github_push', methods=['GET', 'POST'])
def github_push():
    data = request.json
    if data['pusher']['name'] == 'Alyetama':
        return data
    pull_out = os.popen('/usr/bin/git pull').read()
    logger.info(pull_out)
    time.sleep(1)
    subprocess.Popen(['/home/pi/.pyenv/versions/py3.10/bin/python', 'app.py'],
                     shell=False)
    return data


if __name__ == '__main__':
    load_dotenv()
    logger.add('logs.log')
    app.run(host=os.environ['HOST'], port=int(os.environ['PORT']))
