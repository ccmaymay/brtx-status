#!/usr/bin/env python

import json
import logging
import platform
from subprocess import run
from time import time

import boto3

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    level='INFO'
)

BUCKET_NAME = 'brtx-status'
COMMAND = (
    'nvidia-smi',
    '--query-gpu=utilization.gpu,memory.used,memory.total',
    '--format=csv,noheader,nounits',
)


def parse_line(line):
    values = [v.strip() for v in line.split(',')]
    return {
        'utilization': float(values[0]),
        'memory_used': int(values[1]),
        'memory_total': int(values[2]),
    }


timestamp = int(time())
logging.info(f'Timestamp: {timestamp}')

host = platform.node().split('.', 1)[0]
logging.info(f'Host: {host}')

logging.info('Querying GPU status')
status = {
    'host': host,
    'timestamp': timestamp,
    'gpus': [
        parse_line(line)
        for line in run(
            COMMAND,
            check=True, capture_output=True, text=True,
        ).stdout.strip().split('\n')
    ],
}

key_name = f'{host}.json'
logging.info(f'Pushing status to s3://{BUCKET_NAME}/{key_name}')
s3 = boto3.resource('s3')
s3.Bucket(BUCKET_NAME).put_object(
    Key=key_name,
    Body=json.dumps(status).encode('utf-8')
)

logging.info('Done')
