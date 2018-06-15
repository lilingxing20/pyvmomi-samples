# -*- coding:utf-8 -*-

from __future__ import absolute_import

from session import VcenterInfo
from session import VcenterSessionManager

class VMwareClient(VcenterSessionManager):
    def __init__(self, vcenter_info):
        print('vmware client init')
        self.session = self.get_vcenter_session(vcenter_info)

vc_info = VcenterInfo('172.30.126.41', 'administrator@vsphere.local', 'password')
vclient = VMwareClient(vc_info)
print(vclient.session.get_session_id())

vclient2 = VMwareClient(vc_info)
print(vclient2.session.get_session_id())
vclient2.clear(vc_info)

vclient3 = VMwareClient(vc_info)
print(vclient3.session.get_session_id())
vclient3.clear(vc_info)
