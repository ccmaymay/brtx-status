#!/usr/bin/env python

import json
import platform
from subprocess import run
from time import time
from typing import Any, Dict, Sequence

import boto3

BUCKET_NAME = 'brtx-status'
DF_COMMAND = (
    'df',
    '-BG',
)
FREE_COMMAND = (
    'free',
    '-g',
    '-w',
)
MOUNTPOINTS_TO_WATCH = ('/srv/local1', '/srv/local2')
NVIDIA_SMI_COMMAND = (
    'nvidia-smi',
    '--query-gpu=utilization.gpu,memory.used,memory.total',
    '--format=csv,noheader,nounits',
)


def run_command_and_return_stdout(command: Sequence[str]) -> str:
    return run(command, check=True, capture_output=True, text=True).stdout


def parse_nvidia_smi_line(line: str) -> Dict[str, Any]:
    values = [v.strip() for v in line.split(',')]
    return {
        'utilization': float(values[0]),
        'memory_used': int(values[1]),
        'memory_total': int(values[2]),
    }


def parse_df_line(line: str) -> Dict[str, Any]:
    [device, size, used, available, usage_percent, mountpoint] = line.split()
    return {
        'mountpoint': mountpoint,
        'storage_used': int(used[:-1] if used.endswith('G') else used),
        'storage_total': int(size[:-1] if size.endswith('G') else size),
    }


def parse_free_line(line: str) -> Dict[str, Any]:
    [name, total, used] = line.split()[:3]
    return {
        'name': (name[:-1] if name.endswith(':') else name).lower(),
        'memory_used': int(used),
        'memory_total': int(total),
    }


def get_mountpoint(disk_status: Dict[str, Any]) -> str:
    return disk_status['mountpoint']


timestamp = int(time())

host = platform.node().split('.', 1)[0]

free_status_dict = dict(
    (free_status['name'], dict((k, v) for (k, v) in free_status.items() if k != 'name'))
    for free_status in [
        parse_free_line(line)
        for (i, line) in enumerate(run_command_and_return_stdout(FREE_COMMAND).strip().split('\n'))
        if i > 0
    ]
)

status = {
    'host': host,
    'timestamp': timestamp,
    'gpus': [
        parse_nvidia_smi_line(line)
        for line in run_command_and_return_stdout(NVIDIA_SMI_COMMAND).strip().split('\n')
    ],
    'disks': sorted(
        [
            disk_status
            for disk_status in [
                parse_df_line(line)
                for (i, line) in enumerate(run_command_and_return_stdout(DF_COMMAND).strip().split('\n'))
                if i > 0
            ]
            if disk_status['mountpoint'] in MOUNTPOINTS_TO_WATCH
        ],
        key=get_mountpoint,
    ),
    'memory': free_status_dict['mem'],
    'swap': free_status_dict['swap'],
}

key_name = f'{host}.json'
s3 = boto3.resource('s3')
s3.Bucket(BUCKET_NAME).put_object(
    Key=key_name,
    Body=json.dumps(status).encode('utf-8')
)
