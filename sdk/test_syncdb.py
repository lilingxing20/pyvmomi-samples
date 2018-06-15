#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import

from session import VcenterInfo
from session import VcenterSessionManager
from tools import sync_utils

class VMwareClient(VcenterSessionManager):
    def __init__(self, vcenter_info):
        self.session = self.get_vcenter_session(vcenter_info)

vc_info = VcenterInfo('172.30.126.41', 'administrator@vsphere.local', 'password')
vclient = VMwareClient(vc_info)
#print(vclient.session.get_session_id())



#hosts = sync_utils.get_host_properties(vclient.session.si, key='moid')
#clusters = sync_utils.get_cluster_properties(vclient.session.si, key='moid')
dss = sync_utils.get_ds_properties(vclient.session.si, key='moid')

#import pdb;pdb.set_trace()

#print(hosts)
#print(clusters)
print(dss)

vclient.clear(vc_info)
