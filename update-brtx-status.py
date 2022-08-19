#!/usr/bin/env python

import json
import logging
import platform
from subprocess import run
from time import sleep, time

import boto3

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    level='INFO'
)

host = platform.node().split('.', 1)[0]
logging.info(f'Host: {host}')

while True:
    timestamp = int(time())
    logging.info(f'Starting update at {timestamp}...')
    status = {
        'host': host,
        'timestamp': timestamp,
        'gpus': [
            {'load': float(line.split(',')[0].strip())}
            for line in run(
                (
                    'nvidia-smi',
                    '--query-gpu=utilization.gpu,memory.used,memory.total',
                    '--format=csv,noheader,nounits',
                ),
                check=True, capture_output=True, text=True
            ).stdout.strip().split('\n')
        ],
    }

    s3 = boto3.resource('s3')
    s3.Bucket('brtx-status').put_object(
        Key=f'{host}.json',
        Body=json.dumps(status).encode('utf-8')
    )

    logging.info('Update done')
    sleep(15)
