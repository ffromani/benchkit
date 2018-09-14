#!/usr/bin/env python3
# (C) 2018 Red Hat Inc.
# License: Apache v2

import yaml
from pssh.clients import ParallelSSHClient
import gevent

import argparse
import copy
import json
import logging
import os.path
import subprocess
import sys
import time
import uuid


_AUTH_METHODS = ("password",)


def configure():
    bench_id = str(uuid.uuid4())
    parser = argparse.ArgumentParser(
        description="A benchmark tool for VMs")
    parser.add_argument("-t", "--timeout", type=int, default=120,
                        help="time (seconds) to wait for the VMs to come up"
                        " - use 0 to disable")
    parser.add_argument("-U", "--bench-id", type=str, default=bench_id,
                        help="unique identifier for this run")
    parser.add_argument("-H", "--hosts", type=str, default="/etc/hosts",
                        help="host map to run the benchmark in."
                        " Use '-' to read from stdin.")
    parser.add_argument("-A", "--auth-file", type=str, default="auth.json",
                        help="configuration for authentication")
    parser.add_argument("-r", "--root", type=str, default="/tmp/benchkit",
                        help="payload root directory on benchmarked VMs")
    parser.add_argument("payload")

    return parser.parse_args(sys.argv[1:])


def check_auth(auth):
    for key in ('user', 'method', 'details'):
        if key not in auth:
            raise ValueError('malformed auth, missing key: %s' % key)

    if auth['method'] == 'password':
        if 'password' not in auth['details']:
            raise ValueError('password auth set, but password field missing')

    return auth


def read_auth(path):
    with open(path, 'rt') as src:
        return check_auth(json.load(src))


def parse_hosts(src):
    ret = {}
    for line in src:
        data = line.strip()
        if data.startswith('#'):
            continue
        items = data.split()
        if len(items) < 2:
            continue
        vm_ip, vm_name = items[0], items[1]
        ret[vm_name] = vm_ip

    return ret


def read_hosts(path):
    if path != '-':
        src = open(path, 'rt')
    else:
        src = sys.stdin

    ret = parse_hosts(src)

    if path != '-':
        src.close()

    return ret


def make_client(auth, hosts):
    if auth['method'] == 'password':
        return ParallelSSHClient(
            hosts.values(),
            user=auth['user'],
            password=auth['details']['password'])

    raise RuntimeError('unsupported auth method: %s' % auth['method'])


def CommandFailed(RuntimeError):
    def __init__(self, host, output):
        self.host
        self._output = output

    def __str__(self):
        return "Failed on %s: %s" % (self.host, self._output)


def run_hosts(client, cmd, timeout, info=None):
    output = client.run_command(cmd)
    client.join(output, timeout=timeout)   # will raise Timeout

    for host, host_output in output.items():
        if host_output.exit_code != 0:
            raise CommandFailed(host, host_output)

    logging.info('OK: %s'  % (info if info is None else '{%s}' % cmd))


def write_report(name, content):
    with open(name, 'wt') as dst:
        for host, data in content.items():
            dst.write('### %s\n' % host)
            dst.write('%s\n' % data)


def process_output(output, bench_id):
    result, errors = {}, {}
    for host, host_output in output.items():
        if host_output.exit_code == 0:
            result[host] = '\n'.join(host_output.stdout)
        else:
            errors[host] = '\n'.join(host_output.stderr)

    if errors:
        write_report('%s-errors' % bench_id, errors)
        return -1

    write_report('%s-result' % bench_id, result)
    return 0


def upload_payload(client, src_path, dst_dir):
    payload = os.path.basename(src_path)
    dst_path = os.path.join(dst_dir, payload)
    logging.info('%s -> %s', src_path, dst_path)
    cmds = client.copy_file(src_path, dst_path)
    gevent.joinall(cmds, raise_error=True)
    return dst_path


def runbench(args):
    hosts = read_hosts(args.hosts)
    auth = read_auth(args.auth_file)
    client = make_client(auth, hosts)

    # step 1: ensure all hosts are ready to accept commands
    run_hosts(client, '/usr/bin/mkdir -p %s' % args.root, args.timeout)
    # step 2: upload the payload
    remote_payload = upload_payload(client, args.payload, args.root)
    # step 3: unpack the payload
    run_hosts(client, 
              '/usr/bin/tar xz -C {root} -f {payload}'.format(
                root=args.root, payload=remote_payload),
               args.timeout)
    # step 4: run the payload and collect the results
    output = client.run_command(
        'cd {root} && /usr/bin/env BENCH_ROOT={root} {root}/payload.sh'.format(root=args.root))
    client.join(output)  # intentionally no timeout

    return process_output(output, args.bench_id)


def _main():
    args = configure()

    logging.basicConfig(
        format='%(asctime)s' + ' %s ' % args.bench_id + '%(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=logging.DEBUG
    )

    return runbench(args)


if __name__ == "__main__":
    sys.exit(_main())
