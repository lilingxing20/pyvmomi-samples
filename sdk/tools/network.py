# -*- coding:utf-8 -*-

"""
@@ function:
@ network_info_json: get network details

"""


from pyVmomi import vim


def network_info_json(net_obj):
    """
    To json information for a particular network
    @ net_obj: vim.Network
    """
    net_details = {}
    net_details['name'] = net_obj.name
    net_details['overallStatus'] = net_obj.overallStatus

    hosts = []
    for h in net_obj.host:
        hosts.append(h.name)
    net_details['host'] = hosts

    vms = []
    for vm in net_obj.vm:
        vms.append(vm.name)
    net_details['vm'] = vms

    return net_details
