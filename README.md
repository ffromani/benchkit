# BenchKit - a benchmarking toolkit for VMs, either on bare metal or running on KubeVirt

## Audience

BenchKit is a toolkit aimed to developers or power users. BenchKit concerns itself with running and collecting
the benchmark results, trying to be as much automation-friendly as possible.
In particular, BenchKit wants to be ansible-friendly, but at the moment we intentionally avoid ties with any
well known automation solution, trying to be self-contained and generic

## Design and implementation

In a nutshell, running a benchmark consists in

1. set up a well known environment meeting certain criterias
2. running a well defined program in the environment
3. collect the results
4. tear down the environment
5. store the results, compare them

BenchKit concerns itself with steps 1-4.
It is implemented in a multi-staged approach with a series of script and an orchestration tool.

1. `kvrun` does the setup and teardown of VMs on a KubeVirt environment. It ensures N replicas of the given VM object are setup and are run.
   Furthermore, `kvrun` produces a mapping of VMs and their IPs (think like /etc/hosts)
2. `vmrun` takes a mapping of VMs and their IPs (like it is produced by kvrun) and a payload; a payload is a `tgz` archive meeting some criterias documented below.
   `vmrun` upload the payload on all the configured VMs, unpacks it and runs the payload entry point on all the given VMs. Finally, `vmrun` collects
   back the output of the entry point (stdout). All the errors (stderr) are collected into a log file.
   Please note that from the `vmrun` perspective is not relevant if the given VMs are run on bare metal, on kubevirt or anywhere else.
3. the benchmark payload spec
4. `kvbench` is an orchestration tool leveraging both `kvrun` and `vmrun`
5. both `kvrun` and `vmrun` have user-configurable timeouts. If *all* the VMs are not ready (definition of 'ready' depends on the tool) once timeout is expired,
   they abort with error.

## Benchmark payload specification (v1.1)

TODO: add a lint tool

1. the payload is any `tgz` (gzip-compressed tar file)
2. the payload will be uploaded on the VM, and decompressed on the given root directory. The default is `/opt/benchkit`
3. the payload may overwrite any file in the filesystem, even though this is strongly discouraged. They payload should add content.
4. once the payload is succesfully unpacked, the file "$ROOT/payload.sh" will be run. The `PATH` will *NOT* be set - don't rely on that.
5. the call to "$ROOT/payload.sh" is succesful if it exits with code 0 (zero). Any other exit code is a failure.
6. any output (stdout and stderr) produced by "$ROOT/payload.sh" will be recorded
7. please note that the payload content are *NOT* removed after the execution - even if succesfull, because we cannot guarantee the safeness of the removal - 
   this is because the payload content may overwrite some system files directory
