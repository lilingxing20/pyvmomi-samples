#!/usr/bin/env python
# Copyright (c) 2015 Christian Gerbrandt <derchris@derchris.eu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python port of William Lam's generateHTML5VMConsole.pl
Also ported SHA fingerprint fetching to Python OpenSSL library
"""

import atexit
import OpenSSL
import ssl
import sys
import time

from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from tools import cli


def get_vm(content, name):
    try:
        name = unicode(name, 'utf-8')
    except TypeError:
        pass

    vm = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)

    for c in container.view:
        if c.name == name:
            vm = c
            break
    print vm._moId
    return vm


def get_args():
    """
    Add VM name to args
    """
    parser = cli.build_arg_parser()

    parser.add_argument('-n', '--name',
                        required=True,
                        help='Name of Virtual Machine.')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def get_url(host,user,password,name,port=443):
    """
    Simple command-line program to generate a URL
    to open HTML5 Console in Web browser
    """
    try:
        si = SmartConnectNoSSL(host=host,
                               user=user,
                               pwd=password,
                               port=int(port))
    except Exception as e:
        print 'Could not connect to vCenter host'
        print repr(e)
        sys.exit(1)

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    vm = get_vm(content, name)
    x = vm.AcquireTicket("webmks")
    print x
    url = "wss://" + str(x.host) +":" + str(x.port)   + "/ticket/" + str(x.ticket)
    return url


def main():
    """
    Simple command-line program to generate a URL
    to open HTML5 Console in Web browser
    """
    args = get_args()
    try:
        si = SmartConnectNoSSL(host=args.host,
                               user=args.user,
                               pwd=args.password,
                               port=int(args.port))
    except Exception as e:
        print 'Could not connect to vCenter host'
        print repr(e)
        sys.exit(1)

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    vm = get_vm(content, args.name)
    x = vm.AcquireTicket("webmks")
    print x
    url = "wss://" + str(x.host) +":" + str(x.port)   + "/ticket/" + str(x.ticket)
    print url


if __name__ == "__main__":
    main()

# if __name__ == "__main__":
#     print get_url('172.30.126.41', 'administrator@vsphere.local', 'Password@1', 'allinone')
