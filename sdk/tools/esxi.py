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

    esxi_details["disklun"] = disklun_info_json(esxi_obj.config.storageDevice.scsiLun)

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
