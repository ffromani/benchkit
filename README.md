# BenchKit - a benchmarking toolkit for VMs, either on bare metal or running on KubeVirt

## Audience

BenchKit is a toolkit aimed to developers or power users. BenchKit concerns itself with running and collecting
the benchmark results, trying to be as much automation-friendly as possible.
In particular, BenchKit wants to be ansible-friendly, but at the moment we intentionally avoid ties with any
well known automation solution, trying to be self-contained and generic

## Installation:

TODO

## Design and implementation

In a nutshell, running a benchmark consists in

1. set up a well known environment meeting certain criterias
2. running a well defined program in the environment
3. collect the results
4. tear down the environment
5. store the results, compare them

BenchKit concerns itself with steps 1-4.
It is implemented in a multi-staged approach with a series of script and an orchestration tool.

1. `mkkvenv` does the setup and teardown of VMs on a KubeVirt environment. It ensures N replicas of the given VM object are setup and are run.
   Furthermore, `mkkvenv` produces a mapping of VMs and their IPs (think like /etc/hosts)
2. `runbench` takes a mapping of VMs and their IPs (like it is produced by mkkvenv) and a payload; a payload is a `tgz` archive meeting some criterias documented below.
   `runbench` upload the payload on all the configured VMs, unpacks it and runs the payload entry point on all the given VMs. Finally, `runbench` collects
   back the output of the entry point (stdout). All the errors (stderr) are collected into a log file.
   Please note that from the `runbench` perspective is not relevant if the given VMs are run on bare metal, on kubevirt or anywhere else.
3. the benchmark payload spec
4. `kvbench` is an orchestration tool leveraging both `mkkvenv` and `runbench`
5. both `mkkvenv` and `runbench` have user-configurable timeouts. If *all* the VMs are not ready (definition of 'ready' depends on the tool) once timeout is expired,
   they abort with error.

## Keys and auth

Out of convenience, we assume that the VMs being benchmarked are clones of a master VM, and thus share the same authentication settings.
Thus, benchkit will use the same account details (user/password/permissions) for all the VMs.

At the moment

## Benchmark payload specification (v1.1)

### highlights (aka check this first)

1. the payload is any `tgz` (gzip-compressed tar file)
2. the payload will be uploaded on the VM, and decompressed on the given root directory. The default is `/tmp/benchkit`
3. the payload may overwrite any file in the filesystem, even though this is strongly discouraged. They payload should add content.
4. once the payload is succesfully unpacked, the file "$ROOT/payload.sh" will be run. The `PATH` will *NOT* be set - don't rely on that.
5. the call to "$ROOT/payload.sh" is succesful if it exits with code 0 (zero). Any other exit code is a failure.
6. any output (stdout and stderr) produced by "$ROOT/payload.sh" will be recorded
7. please note that the payload content are *NOT* removed after the execution - even if succesfull, because we cannot guarantee the safeness of the removal - 
   this is because the payload content may overwrite some system files directory

### environment variables

The following variables are guaranteed to be set when the entrypoint "$ROOT/payload.sh" is executed

- BENCH\_ROOT: full path the root directory on the machine being benchmarked. The default is `/tmp/benchkit`

### payloadlint

You can use the `payloadlint` tool to check that the payload you want to run passes some base sanity checks. Example:
```
$ ./scripts/payloadlint -vvv payloads/simplest.tgz 
DEBUG - format: gzip-compressed tar
DEBUG - entrypoint: found payload.sh
DEBUG - entrypoint: regular and executable
INFO - payload: OK
```

## TODOs

In no particular order
- integrate with ssh-agent(s)
- testsuite (requires creating VMs on the fly - and don't ship images in the repo)
