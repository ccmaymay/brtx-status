#!/usr/bin/env python

import json
import platform
from subprocess import run
from time import time
from typing import Any, Dict, List, Sequence

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
LSCPU_COMMAND = (
    'lscpu',
)
MOUNTPOINTS_TO_WATCH = ('/srv/local1', '/srv/local2')
NVIDIA_SMI_COMMAND = (
    'nvidia-smi',
    '--query-gpu=utilization.gpu,memory.used,memory.total',
    '--format=csv,noheader,nounits',
)
UPTIME_COMMAND = (
    'uptime',
)


def make_sinfo_command(host: str) -> Sequence[str]:
    return (
        'sinfo',
        '-N',
        '-h',
        '-n',
        host,
        '-o',
        '%P',
    )


def run_command_and_return_stdout(command: Sequence[str], timeout: int = 5) -> str:
    return run(command, check=True, capture_output=True, text=True, timeout=timeout).stdout


def parse_sinfo(text: str) -> List[str]:
    return [line.strip() for line in text.strip().split('\n') if line.strip()]


def parse_nvidia_smi_line(line: str) -> Dict[str, Any]:
    values = [v.strip() for v in line.split(',')]
    return {
        'utilization': float(values[0]),
        'memory_used': int(values[1]),
        'memory_total': int(values[2]),
        'memory_unit': 'MiB',
    }


def parse_df_line(line: str) -> Dict[str, Any]:
    [device, size, used, available, usage_percent, mountpoint] = line.split()
    return {
        'mountpoint': mountpoint,
        'storage_used': int(used[:-1] if used.endswith('G') else used),
        'storage_total': int(size[:-1] if size.endswith('G') else size),
        'storage_unit': 'GiB',
    }


def parse_free_line(line: str) -> Dict[str, Any]:
    [name, total, used] = line.split()[:3]
    return {
        'name': (name[:-1] if name.endswith(':') else name).lower(),
        'memory_used': int(used),
        'memory_total': int(total),
        'memory_unit': 'GiB',
    }


def parse_uptime_line(line: str) -> Dict[str, Any]:
    load_avgs = [float(t.rstrip(',')) for t in line.strip().split()[-3:]]
    keys = [f'load_avg_{m}_m' for m in (1, 5, 15)]
    return dict(zip(keys, load_avgs))


def parse_lscpu_line(line: str) -> Dict[str, Any]:
    num_cpus = int(line.strip().split()[-1])
    return {'num_cpus': num_cpus}


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

[lscpu_status_dict] = [
    parse_lscpu_line(line)
    for line in run_command_and_return_stdout(LSCPU_COMMAND).strip().split('\n')
    if line.startswith('CPU(s):')
]
uptime_status_dict = parse_uptime_line(run_command_and_return_stdout(UPTIME_COMMAND).strip())

status = {
    'host': host,
    'timestamp': timestamp,
    'gpus': [
        parse_nvidia_smi_line(line)
        for line in run_command_and_return_stdout(NVIDIA_SMI_COMMAND, timeout=30).strip().split('\n')
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
    'load': dict(list(lscpu_status_dict.items()) + list(uptime_status_dict.items())),
    'partitions': parse_sinfo(run_command_and_return_stdout(make_sinfo_command(host))),
}

key_name = f'{host}.json'
s3 = boto3.resource('s3')
s3.Bucket(BUCKET_NAME).put_object(
    Key=key_name,
    Body=json.dumps(status).encode('utf-8')
)
