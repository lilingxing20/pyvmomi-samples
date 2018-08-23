# -*- coding:utf-8 -*-

from __future__ import absolute_import

from session import VcenterInfo
from session import VcenterSessionManager

class VMwareClient(VcenterSessionManager):
    def __init__(self, vcenter_info):
        print('vmware client init')
        self.session = self.get_vcenter_session(vcenter_info)

#vc_info = VcenterInfo('172.30.126.41', 'administrator@vsphere.local', 'Password01!')
#vclient = VMwareClient(vc_info)
#print(vclient.session.get_session_id())
#
#import pdb;pdb.set_trace()
#
#vclient2 = VMwareClient(vc_info)
#print(vclient2.session.get_session_id())
#vclient2.clear(vc_info)
#
#vclient3 = VMwareClient(vc_info)
#print(vclient3.session.get_session_id())
#vclient3.clear(vc_info)


import multiprocessing
import time

def callback_error(ex):
    print(ex)
def callback_vcenter(ex):
    print(ex)

def async_dc(vclient):
    print(vclient)
    print(vclient.session.get_session_id())
    return None


if __name__ == '__main__':
    print('a')
    vc_info = VcenterInfo('172.30.126.41', 'administrator@vsphere.local', 'Password01!')
    vclient = VMwareClient(vc_info)
    print(vclient.session.get_session_id())
    print(vc_info)
    try:
        pool = multiprocessing.Pool(processes=1)
        for i in range(4):
            pool.apply_async(async_dc, args=(vclient,), callback=callback_vcenter, error_callback=callback_error)
        pool.close()
        time.sleep(1000)
    except Exception as ex:
        print(ex)

