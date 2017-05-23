# -*- coding:utf-8 -*-

"""
@@ function:
@ datacenter_info_json: get datacenter details
@ resource_pool_info_json: get resource pool details
@ vapp_info_json: get vApp details
@ cluster_info_json: get cluster details

"""

from pyVmomi import vim
import esxi


def datacenter_info_json(dc_obj):
    """
    To json information for a particular datacenter
    @ dc_obj: vim.Datacenter
    """
    dc_details = {}
    dc_details['name'] = dc_obj.name
    dc_details['tag'] = dc_obj.tag
    dc_details['overallStatus'] = dc_obj.overallStatus

    networks = []
    for net in dc_obj.network:
        networks.append(net.name)
    dc_details['network'] = networks

    datastores = []
    for ds in dc_obj.datastore:
        datastores.append(ds.name)
    dc_details['datastore'] = datastores

    return dc_details


def resource_pool_info_json(pool_obj):
    """
    To json information for a particular resource pool
    @ pool_obj: vim.ResourcePool
    """
    pool_details = {}
    pool_details['name'] = pool_obj.name
    pool_details['cpuAllocation'] = pool_obj.config.cpuAllocation.reservation
    pool_details['memoryAllocation'] = pool_obj.config.memoryAllocation.reservation
    pool_details['overallStatus'] = pool_obj.overallStatus
    pool_details['owner_cluster'] = pool_obj.owner.name

    vms = []
    for vm in pool_obj.vm:
        vms.append(vm.name)
    pool_details['vm'] = vms

    return pool_details


def vapp_info_json(vapp_obj):
    """
    To json information for a particular vApp
    @ vapp_obj: vim.VirtualApp
    """
    vapp_details = {}

    vapp_details['name'] = vapp_obj.name
    vapp_details['cpuAllocation'] = vapp_obj.config.cpuAllocation.reservation
    vapp_details['memoryAllocation'] = vapp_obj.config.memoryAllocation.reservation
    vapp_details['overallStatus'] = vapp_obj.overallStatus
    vapp_details['owner_cluster'] = vapp_obj.owner.name

    vms = []
    for vm in vapp_obj.vm:
        vms.append(vm.name)
    vapp_details['vm'] = vms

    nets = []
    for net in vapp_obj.network:
        nets.append(net.name)
    vapp_details['network'] = nets

    return vapp_details


def cluster_info_json(cluster_obj):
    """
    To json information for a particular cluster computer resource
    @ cluster_obj: vim.ClusterComputeResource
    """
    cluster_details = {}
    cluster_details["name"] = cluster_obj.name
    cluster_details["numLun"] = len(cluster_obj.datastore)

    summary = cluster_obj.summary
    cluster_details["numHosts"] = summary.numHosts
    cluster_details["numEffectiveHosts"] = summary.numEffectiveHosts

    cluster_details["hosts"] = []
    for host_obj in cluster_obj.host:
        host_details = esxi.esxi_info_json(host_obj)
        cluster_details["hosts"].append(host_details)

    return cluster_details
