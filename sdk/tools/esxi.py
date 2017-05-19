# -*- coding:utf-8 -*-

"""
@@ function:
@ esxi_info_json: get esxi details

"""


from pyVmomi import vim


def esxi_info_json(esxi_obj):
    """
    To json information for a particular esxi host
    @ esxi_obj: vim.HostSystem
    """
    esxi_details = {}
    esxi_details['name'] = esxi_obj.name

    networks = []
    for net in esxi_obj.network:
        networks.append(net.name)
    esxi_details['network'] = networks

    datastores = []
    for ds in esxi_obj.datastore:
        datastores.append(ds.name)
    esxi_details['datastore'] = datastores

    vms = []
    for vm in esxi_obj.vm:
        vms.append(vm.name)
    esxi_details['vm'] = vms

    return esxi_details
