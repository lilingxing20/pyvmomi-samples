# -*- coding:utf-8 -*-

"""
@@ function:
@ datacenter_info_json: get datacenter details
@ resource_pool_info_json: get resource pool details
@ vapp_info_json: get vApp details
@ cluster_info_json: get cluster details

"""

from pyVmomi import vim


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
        host_details = {}
        host_details["name"] = host_obj.name
        host_details["tag"] = host_obj.tag
        host_details["model"] = host_obj.summary.hardware.model
        host_details["cpuMhz"] = host_obj.summary.hardware.cpuMhz
        host_details["cpuModel"] = host_obj.summary.hardware.cpuModel
        host_details["numCpuCores"] = host_obj.summary.hardware.numCpuCores
        host_details["numCpuPkgs"] = host_obj.summary.hardware.numCpuPkgs
        host_details["memorySize"] = host_obj.summary.hardware.memorySize
        host_details["product"] = host_obj.config.product.__dict__
        host_details["memoryAllocation"] = host_obj.systemResources.config.memoryAllocation.reservation
        host_details["cpuAllocation"] = host_obj.systemResources.config.cpuAllocation.reservation

        host_details["disklun"] = disklun_info_json(host_obj.config.storageDevice.scsiLun)
        host_details["datastore"] = datastore_info_json(host_obj.datastore)

        cluster_details["hosts"].append(host_details)

    return cluster_details


def disklun_info_json(scsilun_objs):
    """
    To json information for a particular esxi host disk lun
    @ scsilun_objs: vim.host.ScsiLun
    @@  vim.host.ScsiDisk
    """
    scsiluns_info = []
    for lun_obj in scsilun_objs:
        if not isinstance(lun_obj, vim.host.ScsiDisk):
            continue
        lun_info = {}
        lun_info['deviceName'] = lun_obj.deviceName
        lun_info['displayName'] = lun_obj.displayName
        lun_info['canonicalName'] = lun_obj.canonicalName
        lun_info['vendor'] = lun_obj.vendor
        lun_info['blockSize'] = lun_obj.capacity.blockSize
        lun_info['block'] = lun_obj.capacity.block
        lun_info['devicePath'] = lun_obj.devicePath
        lun_info['ssd'] = lun_obj.ssd
        lun_info['localDisk'] = lun_obj.localDisk

        scsiluns_info.append(lun_info)

    return scsiluns_info


def datastore_info_json(ds_objs):
    """
    To json information for a particular esxi host datastore
    @ scsilun_objs: vim.host.ScsiLun
    @@  vim.host.ScsiDisk
    """
    dss_info = []
    for ds_obj in ds_objs:
        ds_info = {}
        ds_info['name'] = ds_obj.name
        ds_info['tag'] = ds_obj.tag
        ds_info['capacity'] = ds_obj.summary.capacity
        ds_info['freeSpace'] = ds_obj.summary.freeSpace
        ds_info['url'] = ds_obj.summary.url
        ds_info['accessible'] = ds_obj.summary.accessible
        ds_info['multipleHostAccess'] = ds_obj.summary.multipleHostAccess
        ds_info['type'] = ds_obj.summary.type
        ds_info['ssd'] = ds_obj.info.vmfs.ssd
        ds_info['local'] = ds_obj.info.vmfs.local

        dss_info.append(ds_info)

    return dss_info
