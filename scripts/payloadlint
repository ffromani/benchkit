#!/usr/bin/env python3
# (C) 2018 Red Hat Inc.
# License: Apache v2

import argparse
import logging
import os.path
import stat
import sys
import tarfile


_ENTRYPOINT = 'payload.sh'


def find_entrypoint(tar):
    for info in tar.getmembers():
        if os.path.normpath(info.name) == _ENTRYPOINT:
            return info
    return None


def lint(payload):
    try:
        tar = tarfile.open(payload, mode='r:gz')
    except (OSError, tarfile.TarError):
        logging.error('format: unsupported %s' % payload)
        return -1
    logging.debug('format: gzip-compressed tar')

    entrypoint = find_entrypoint(tar)
    if entrypoint is None:
        logging.error('entrypoint: missing payload.sh')
        return -1
    logging.debug('entrypoint: found %s' % _ENTRYPOINT)

    if not entrypoint.isfile():
        logging.error('entrypoint: not regular file')
        return -1
    if not (entrypoint.mode & (stat.S_IRUSR|stat.S_IXUSR)):
        logging.error('entrypoint: not executable')
    logging.debug('entrypoint: regular and executable')

    logging.info('payload: OK')
    return 0
    


def level_from_verbose(verbose):
    if verbose is not None:
        if verbose >= 2:
            return logging.DEBUG
        if verbose >= 1:
            return logging.INFO
    return logging.WARNING


def _main():
    parser = argparse.ArgumentParser(
        description="A payload file linter tool")
    parser.add_argument("-v", "--verbose", action="count",
                        help="increase the verbosiness level")
    parser.add_argument("payload")

    args = parser.parse_args(sys.argv[1:])

    logging.basicConfig(format='%(levelname)s - %(message)s',
                        level=level_from_verbose(args.verbose))
    return lint(args.payload)


if __name__ == "__main__":
    sys.exit(_main())
