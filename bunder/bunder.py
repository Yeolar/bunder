#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018 Yeolar
#

import argparse
import fabric
import imp
import os
import shutil
import sys

from .transfer import Transfer
from .util import *


PROG_NAME = 'bunder'

conf = config('.bunder.yml')


def basename(name):
    return name.split('-')[0]

def fullname(name, deb=False):
    return '%s-Linux' % name + (deb and '.deb' or '.tar.xz')


class Handler(object):

    def __init__(self):
        self.c = fabric.Connection(
                conf.source.host,
                connect_kwargs={'password': conf.source.password})

    def build_path(self, name):
        return os.path.join(conf.build.path, basename(name))

    def remote_path(self, name):
        return os.path.join(conf.source.path, fullname(name))

    def package(self, project):
        return [os.path.join(conf.build.path, i)
                for i in os.listdir(conf.build.path)
                if i.startswith(project) and
                   os.path.splitext(i)[1] in ('.deb', '.xz')]


class PkgPackHandler(Handler):

    PACK_CMD = 'dpkg-scanpackages . | gzip - > Packages.gz'

    def __init__(self):
        Handler.__init__(self)

    def __call__(self, path):
        print 'pack: %s' % path
        remote = os.path.join(conf.source.path, os.path.basename(path))
        direct = os.path.dirname(remote)
        Transfer(self.c).put(path, remote)
        if os.path.splitext(path)[1] == '.deb':
            self.c.run('cd %s && %s' % (direct, self.PACK_CMD))


class DepInstallHandler(Handler):

    def __init__(self):
        Handler.__init__(self)

    def __call__(self, dep):
        print 'install dep: %s' % dep
        direct = os.path.join(self.build_path(dep), basename(dep))
        target = os.path.join(self.build_path(dep), fullname(dep))
        if os.path.exists(target):
            print '  already installed.'
            return
        if not os.path.exists(direct):
            os.makedirs(direct, 0755)
        Transfer(self.c).get(self.remote_path(dep), target)
        self.c.local('tar xJf %s -C %s --strip-components=1' % (target, direct))


class DepRemoveHandler(Handler):

    def __init__(self):
        Handler.__init__(self)

    def __call__(self, dep):
        print 'remove dep: %s' % dep
        shutil.rmtree(self.build_path(dep))


def pkg_pack(names):
    handler = PkgPackHandler()
    map(handler, names and names or handler.package(conf.project))


def dep_install(names):
    handler = DepInstallHandler()
    map(handler, names and names or conf.depend)


def dep_remove(names):
    handler = DepRemoveHandler()
    map(handler, names and names or conf.depend)


def main():
    ap = argparse.ArgumentParser(
            prog=PROG_NAME,
            description='Bunder tool.',
            epilog='Author: Yeolar <yeolar@gmail.com>',
            add_help=False)
    ag = ap.add_argument_group('package')
    ag.add_argument('-p', '--pack',
                    action='store', nargs='*', metavar='pkg',
                    help='pack package to deb host.')
    ag = ap.add_argument_group('dependency')
    ag.add_argument('-i', '--dep-install',
                    action='store', nargs='*', metavar='dep',
                    help='initialize dependencies.')
    ag.add_argument('-r', '--dep-remove',
                    action='store', nargs='*', metavar='dep',
                    help='clean dependencies.')
    ag = ap.add_argument_group('others')
    ag.add_argument('-h', '--help',
                    action='store_true',
                    help='show help')
    args = ap.parse_args()

    if args.pack is not None:
        pkg_pack(args.pack)
        return
    if args.dep_install is not None:
        dep_install(args.dep_install)
        return
    if args.dep_remove is not None:
        dep_remove(args.dep_remove)
        return

    ap.print_help()


if __name__ == '__main__':
    main()
