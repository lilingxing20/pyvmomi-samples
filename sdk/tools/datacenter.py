# -*- coding:utf-8 -*-

"""
@@ function:
@ get_datastore_detail: get datacenter details

"""

from pyVmomi import vim

import utils
import vm


def get_datacenter_detail(content, dc_obj):
    """
    To json information for a particular datacenter
    @ dc_obj: vim.Datacenter
    """
    dc_details = {}
    dc_details['name'] = dc_obj.name
    dc_details['tag'] = dc_obj.tag

    # get clusters info
    clusters_info = []
    cluster_objs = utils.get_objs(content, dc_obj.hostFolder, [vim.ClusterComputeResource])
    for obj in cluster_objs:
        cluster = get_cluster_detail(content, obj)
        clusters_info.append(cluster)
    dc_details['cluster'] = clusters_info
    return dc_details


def get_cluster_detail(content, cluster_obj):
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

    # get hosts info
    hosts_info = []
    for host_obj in cluster_obj.host:
        host_info = get_host_detail(host_obj)
        hosts_info.append(host_info)
    cluster_details["host"] = hosts_info

    # get datastores info
    datastores_info = []
    for ds_obj in cluster_obj.datastore:
        ds_info = get_datastore_detail(ds_obj)
        datastores_info.append(ds_info)
    cluster_details["datastore"] = datastores_info

    return cluster_details


def get_host_detail(esxi_obj):
    """
    To json information for a particular esxi host
    @ esxi_obj: vim.HostSystem
    """
    esxi_details = {}
    esxi_details['name'] = esxi_obj.name
    esxi_details['connectionState'] = esxi_obj.runtime.connectionState
    esxi_details['powerState'] = esxi_obj.runtime.powerState
    esxi_details['bootTime'] = esxi_obj.runtime.bootTime
    esxi_details['hostName'] = esxi_obj.config.network.dnsConfig.hostName
    esxi_details['domainName'] = esxi_obj.config.network.dnsConfig.domainName
    esxi_details['biosVersion'] = esxi_obj.hardware.biosInfo.biosVersion
    esxi_details['numCpuPkgs'] = esxi_obj.hardware.cpuInfo.numCpuPackages
    esxi_details['numCpuCores'] = esxi_obj.hardware.cpuInfo.numCpuCores
    esxi_details['numCpuThreads'] = esxi_obj.hardware.cpuInfo.numCpuThreads
    esxi_details['hz'] = esxi_obj.hardware.cpuInfo.hz
    esxi_details['memorySize'] = esxi_obj.hardware.memorySize
    esxi_details['vendor'] = esxi_obj.hardware.systemInfo.vendor
    esxi_details['model'] = esxi_obj.hardware.systemInfo.model
    esxi_details['uuid'] = esxi_obj.hardware.systemInfo.uuid
    esxi_details['overallCpuUsage'] = esxi_obj.summary.quickStats.overallCpuUsage
    esxi_details['overallMemoryUsage'] = esxi_obj.summary.quickStats.overallMemoryUsage
    esxi_details['managementServerIp'] = esxi_obj.summary.managementServerIp
    esxi_details["cpuMhz"] = esxi_obj.summary.hardware.cpuMhz
    esxi_details["cpuModel"] = esxi_obj.summary.hardware.cpuModel
    esxi_details["memoryAllocation"] = esxi_obj.systemResources.config.memoryAllocation.reservation
    esxi_details["cpuAllocation"] = esxi_obj.systemResources.config.cpuAllocation.reservation

    product_info = esxi_obj.summary.config.product.__dict__
    product_info.pop('dynamicProperty')
    product_info.pop('dynamicType')
    esxi_details['product'] = product_info

    # get vms info
    vms_info = []
    for obj in esxi_obj.vm:
        vm = get_vm_detail(obj)
        vms_info.append(vm)
    esxi_details['vm'] = vms_info

    return esxi_details


def get_datastore_detail(ds_obj):
    """
    To json information for a particular datastore
    @ ds_obj: vim.Datastore
    """
    ds_details = {}
    ds_details['name'] = ds_obj.name
    ds_details['tag'] = ds_obj.tag
    ds_details['overallStatus'] = ds_obj.overallStatus
    ds_details['capacity'] = ds_obj.summary.capacity
    ds_details['freeSpace'] = ds_obj.summary.freeSpace
    ds_details['url'] = ds_obj.summary.url
    ds_details['accessible'] = ds_obj.summary.accessible
    ds_details['multipleHostAccess'] = ds_obj.summary.multipleHostAccess
    ds_details['type'] = ds_obj.summary.type
    ds_details['ssd'] = ds_obj.info.vmfs.ssd
    ds_details['local'] = ds_obj.info.vmfs.local
    return ds_details


def get_vm_detail(vm_obj):
    """
    To json information for a particular virtual machine
    @ vm_obj: vim.VirtualMachine
    """
    return vm.vm_info_json(vm_obj)
