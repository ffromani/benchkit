#!/usr/bin/env python3
# (C) 2018 Red Hat Inc.
# License: Apache v2


from collections import namedtuple
import os.path

import pytest

import runbench


def test_check_auth_ok():
    auth = {
    	"user": "root",
	    "method": "password",
    	"details": {
	    	"password": "unsafe"
    	}
    }
    assert auth == runbench.check_auth(auth)


@pytest.mark.parametrize('auth', [
    ({}),
    ({
        "user": "root"
    }),
    ({
        "user": "root",
        "method": "password",
        "details": {}
    }),
    ({
        "user": "root",
        "method": "password",
        "details": {}
    }),
    ({
        "user": "root",
        "method": "password",
        "details": {
            "foo": "bar",
        }
    }),
])
def test_check_auth_malformed(auth):
    with pytest.raises(ValueError):
        runbench.check_auth(auth)


def test_read_hosts_ok():
    assert runbench.read_hosts("/etc/hosts")


@pytest.mark.parametrize('data', [
    ([
        "127.0.0.1"
    ]),
    ([
        "localhost"
    ]),
])
def test_read_hosts_malformed(data):
    assert runbench.parse_hosts(data) == {}


FakeHostOutput = namedtuple(
    'FakeHostOutput', ['exit_code', 'stdout', 'stderr'])


def test_process_output_ok(tmpdir):
    output = {
            "foobar": FakeHostOutput(
                exit_code=0,
                stdout=["everything OK"],
                stderr=["test failed"]
            ),
    }
    basepath = os.path.join(tmpdir, "test")
    runbench.process_output(output, basepath)
    with open(basepath + "-result") as f:
        data = f.read()
    assert data == """### foobar
everything OK
"""


def test_process_output_failed(tmpdir):
    output = {
            "foobar": FakeHostOutput(
                exit_code=2,
                stdout=["everything OK"],
                stderr=["test failed"]
            ),
    }
    basepath = os.path.join(tmpdir, "test")
    runbench.process_output(output, basepath)
    with open(basepath + "-errors") as f:
        data = f.read()
    assert data == """### foobar
test failed
"""
