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

import os
import sys
import atexit

from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim


def create_console_html(vm_name, wmks_url):
    console_html = """
<!DOCTYPE html PUBLIC"-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml"> 
  <head> 
    <meta http-equiv="content-type" content="text/html; charset=utf-8" /> <title>Console</title> 
  </head> 
  <body> <link rel="stylesheet" type="text/css" href="css/wmks-all.css" /> 
    <script type="text/javascript" src="jquery.js"></script> 
    <script type="text/javascript" src="jquery-ui.min.js"></script> 
    <script type="text/javascript" src="wmks.min.js" type="text/javascript"></script> 
    <div id="wmksContainer" style="position:absolute;width:100%;height:100%"></div>  
    <script> 
      var wmks = WMKS.createWMKS("wmksContainer",{}).register(WMKS.CONST.Events.CONNECTION_STATE_CHANGE, function(event, data){
              if (data.state == WMKS.CONST.ConnectionState.CONNECTED) {
                console.log("connection state change : connected");
              }
            });
""" + """
      wmks.connect("%s");
""" % wmks_url + """
    </script > 
  </body> 
</html> """
    base_dir = os.path.split(os.path.realpath(__file__))[0]
    file_path = base_dir + "/console/" + vm_name + ".html"
    with open(file_path, 'w') as f:
        f.write(console_html)
    print(file_path)


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
    # print x
    url = "wss://" + str(x.host) +":" + str(x.port)   + "/ticket/" + str(x.ticket)
    return url


if __name__ == "__main__":
    vm_name = 'node204'
    wmks_url = get_url('172.30.126.40', 'administrator@vsphere.local', 'P@ssw0rd', vm_name)
    create_console_html(vm_name, wmks_url)
