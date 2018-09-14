#!/usr/bin/env python3
# (C) 2018 Red Hat Inc.
# License: Apache v2

import yaml

import argparse
import copy
import json
import logging
import subprocess
import sys
import time


def _configure():
    parser = argparse.ArgumentParser(
        description="VM environment setup/teardown tool for KubeVirt")
    parser.add_argument("-N", "--instances", type=int, default=1,
                        help="number of VMs to run")
    parser.add_argument("-c", "--command", type=str, default="kubectl",
                        help="command to use to control the cluster")
    parser.add_argument("-S", "--setup-only", action="store_true",
                        help="stop after the setup step")
    parser.add_argument("-T", "--teardown-only", action="store_true",
                        help="perform only the teardown step")
    parser.add_argument("-t", "--timeout", type=int, default=120,
                        help="time (seconds) to wait for the VMs to come up"
                        " - use 0 to disable")
    parser.add_argument("VM_definition")

    return parser.parse_args(sys.argv[1:])


def customize(vm_master_def, ident):
    vm_def = copy.deepcopy(vm_master_def)
    vm_def['metadata']['name'] = '%s-%i' % (
        vm_def['metadata']['name'],
        ident
    )
    return vm_def


class VMDef:
    def __init__(self, master_def, ident=None):
        self._def = copy.deepcopy(master_def)
        if ident is not None:
            self._def['metadata']['name'] = '%s-%i' % (
                self._def['metadata']['name'],
                ident
            )

    @property
    def name(self):
        return self._def['metadata']['name']

    def to_yaml(self):
        return yaml.dump(self._def)

    def to_bytes(self):
        return self.to_yaml().encode('utf-8')


class POD:
    def __init__(self, pod_def):
        self._def = pod_def

    def related_to(self, vm_def):
        return vm_def.name in self.name

    @property
    def ip(self):
        return self._def["status"]["podIP"]

    @property
    def ready(self):
        return all(
            cs["ready"]
            for cs in self._def["status"]["containerStatuses"]
        )

    @property
    def phase(self):
        return self._def["status"]["phase"]

    @property
    def name(self):
        return self._def["metadata"]["name"]


class Cmd:
    def __init__(self, exe):
        self._exe = exe

    def create(self, vm_def):
        return self._run('create', vm_def)

    def delete(self, vm_def):
        return self._run('delete', vm_def)

    def readiness_status(self, vm_defs):
        ret = {}
        for pod in self.get_pods():
            for vm_def in vm_defs:
                if pod.related_to(vm_def):
                    ret[vm_def.name] = pod.ready
        return ret

    def get_ips(self, vm_defs):
        ret = {}
        for pod in self.get_pods():
            for vm_def in vm_defs:
                if pod.related_to(vm_def):
                    ret[vm_def.name] = pod.ip
        return ret

    def get_pods(self):
        ret = subprocess.run(
            [self._exe, 'get', 'pods', '-o', 'json'],
            stdout=subprocess.PIPE
        )
        content = json.loads(ret.stdout.decode('utf-8'))
        return set(
            POD(item)
            for item in content["items"]
            if item["kind"] == "Pod"
        )

    def _run(self, action, vm_def):
        ret = subprocess.run(
            [self._exe, action, '-f', '-'],
            input=vm_def.to_bytes(),
            stdout=subprocess.PIPE
        )
        if ret.returncode != 0:
            raise RuntimeError("%s on %s failed" % (action, vm_def.name))
        return ret


def wait_ready(cmd, vm_defs, timeout):
    elapsed = 0  # seconds
    step = 1.0  # seconds
    while True:
        if elapsed >= timeout:
            raise TimeoutError("waited %s seconds" % timeout)

        ready, waiting = set(), set()
        for vm_name, all_ready in cmd.readiness_status(vm_defs).items():
            if all_ready:
                ready.add(vm_name)
            else:
                waiting.add(vm_name)
        if not waiting:
            break

        logging.info(
            "%i/%i VM ready, waiting...", len(ready), len(vm_defs))
        time.sleep(step)
        elapsed += step


def setup(cmd, vm_defs):
    created = []
    for vm_def in vm_defs:
        try:
            cmd.create(vm_def)
        except Exception as exc:
            logging.warning('failed to create: %s', vm_def.name)
        else:
            created.append(vm_def)
            logging.info('created: %s', vm_def.name)
    return created


def teardown(cmd, vm_defs):
    for vm_def in vm_defs:
        # clean as much as we can:
        try:
            cmd.delete(vm_def)
        except Exception as exc:
            logging.warning('cannot delete %s: %s', vm_def.name, exc)
        else:
            logging.info('deleted: %s', vm_def.name)


def dump_hosts(vms, out):
    out.write('# BEGIN %d available VMs\n' % len(vms))
    for vm_name, vm_ip in vms.items():
        out.write('%s\t\t%s\n' % (vm_ip, vm_name))
    out.write('# END %d available VMs\n' % len(vms))
    out.flush()


def _main():
    logging.basicConfig(
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=logging.DEBUG
    )
    
    args = _configure()

    cmd = Cmd(args.command)

    with open(args.VM_definition) as src:
        vm_master_def = yaml.load(src)

    vm_defs = [
        VMDef(vm_master_def, ident) for ident in range(args.instances)
    ]

    logging.info('%d VM definitions', len(vm_defs))
    if not args.teardown_only:
        created = setup(cmd, vm_defs)
    else:
        created = vm_defs

    if args.timeout > 0:
        try:
            wait_ready(cmd, created, args.timeout)
        except TimeoutError:
            return 1

    if not args.setup_only and not args.teardown_only:
        dump_hosts(cmd.get_ips(created), sys.stdout)
        time.sleep(300.)

    if not args.setup_only:
        teardown(cmd, created)
        # TODO: add wait_gone here


if __name__ == "__main__":
    sys.exit(_main())
