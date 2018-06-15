# -*- coding:utf-8 -*-

"""
@@ function:
@ vm_info_json: get VM details

"""
from __future__ import absolute_import, division

import logging

from urllib.request import unquote
from past.utils import old_div
from pyVmomi import vim

from . import constants, utils

LOG = logging.getLogger(__name__)


def vm_info_json(vm_moref):
    """
    To json information for a particular virtual machine
    @ vm_moref: vim.VirtualMachine
    """
    if not vm_moref.config:
        # vm creating
        return None
    vm_details = {}
    vm_details["name"] = vm_moref.summary.config.name
    vm_details["path"] = vm_moref.summary.config.vmPathName
    vm_details["guest"] = vm_moref.summary.config.guestFullName
    vm_details["instance_uuid"] = vm_moref.summary.config.instanceUuid
    vm_details["uuid"] = vm_moref.summary.config.uuid
    vm_details["esxi_host"] = vm_moref.summary.runtime.host.name
    vm_details["state"] = vm_moref.summary.runtime.powerState

    vm_details["tools_version"] = vm_moref.guest.toolsVersion
    vm_details["guest_name"] = vm_moref.guest.guestFullName
    vm_details["guest_id"] = vm_moref.guest.guestId
    vm_details["hostname"] = vm_moref.guest.hostName
    vm_details["guest_state"] = vm_moref.guest.guestState

    vm_details['version'] = vm_moref.config.version
    vm_details["num_cores"] = vm_moref.config.hardware.numCoresPerSocket
    vm_details["num_cpu"] = vm_moref.config.hardware.numCPU
    vm_details["memoryMB"] = vm_moref.config.hardware.memoryMB
    vm_details['is_template'] = vm_moref.config.template

    vm_details['sys_type'] = utils.get_system_type(vm_moref.config)
    vm_details["moid"] = vm_moref._moId

    (vm_disks, net_adapters) = get_vm_device_info(vm_moref.config.hardware.device)
    vm_details['disk'] = vm_disks
    vm_nets = get_vm_nic_info(net_adapters, vm_moref.guest.net)
    vm_details['network'] = vm_nets

    vm_details["ip"] = vm_moref.guest.ipAddress
#    vm_ipv4 = []
#    vm_ipv6 = []
#    for net in vm_moref.guest.net:
#        if net.ipAddress:
#            vm_ipv4.append(net.ipAddress[0])
#            if len(net.ipAddress) >= 2:
#                vm_ipv6.append(net.ipAddress[1])
#    vm_details["ipv4"] = vm_ipv4
#    vm_details["ipv6"] = vm_ipv6
    return vm_details


def vm_net_info(net):
    """
    """
    net_list = []
    for n in net:
        net_info = {}
        net_info['macAddress'] = n.macAddress
        net_info['network'] = n.network
        net_info['ipAddress'] = n.ipAddress
        net_list.append(net_info)
    return net_list


def get_vm_nic_info(net_adapters, vm_net_mo):
    """
    """
    for adapter in net_adapters:
        key = adapter['key']
        for net in vm_net_mo:
            if key != net.deviceConfigId:
                continue
            adapter['portgroup'] = unquote(net.network)
            adapter['connected'] = net.connected
            if not net.ipConfig:
                break
            for ipconfig in net.ipConfig.ipAddress:
                if ipconfig.ipAddress.startswith('fe80'):
                    continue
                adapter['ipv4'] = ipconfig.ipAddress
                adapter['prefix'] = ipconfig.prefixLength
                break
            break
    return net_adapters


def get_vm_device_info(virtual_devices):
    """
    To json information for a particular virtual machine disk
    @ virtual_devices: vim.vm.device.VirtualDevice[]
    @@  vim.vm.device.VirtualPCIController:      key>=100
    @@  vim.vm.device.VirtualIDEController:      key>=200
    @@  vim.vm.device.VirtualPS2Controller:      key>=300
    @@  vim.vm.device.VirtualSIOController:      key>=400
    @@  vim.vm.device.VirtualVideoCard:          key>=500
    @@  vim.vm.device.VirtualKeyboard:           key>=600
    @@  vim.vm.device.VirtualPointingDevice:     key>=700
    @@  vim.vm.device.ParaVirtualSCSIController: key>=1000
    @@  vim.vm.device.VirtualDisk:               key>=2000
    @@  vim.vm.device.VirtualCdrom:              key>=3002
    @@  vim.vm.device.VirtualVmxnet3:            key>=4000
    @@  vim.vm.device.VirtualE1000:              key>=4000
    @@  vim.vm.device.VirtualE1000e:             key>=4000
    @@  vim.vm.device.VirtualFloppy:             key>=8000
    @@  vim.vm.device.VirtualVMCIDevice:         key>=12000
    """
    disks_info = []
    nets_info = []
    scsi_ctls_type = {}
    for dev_moref in virtual_devices:
        if dev_moref.key in [1000, 1001, 1002, 1003]:
            if isinstance(dev_moref, vim.vm.device.ParaVirtualSCSIController):
                scsi_ctls_type[dev_moref.key] = 'ParaVirtual'
            elif isinstance(dev_moref, vim.vm.device.VirtualLsiLogicSASController):
                scsi_ctls_type[dev_moref.key] = 'LsiLogicSAS'
            elif isinstance(dev_moref, vim.vm.device.VirtualLsiLogicController):
                scsi_ctls_type[dev_moref.key] = 'LsiLogic'
            elif isinstance(dev_moref, vim.vm.device.VirtualBusLogicController):
                scsi_ctls_type[dev_moref.key] = 'BusLogic'
            else:
                scsi_ctls_type[dev_moref.key] = None
    for device_moref in virtual_devices:
        if isinstance(device_moref, vim.vm.device.VirtualDisk):
            disk_info = get_vm_disk_info(device_moref, scsi_ctls_type)
            disks_info.append(disk_info)
        elif device_moref.key >= 4000 and device_moref.key < 4100:
            # Retrieve the virtual machine before one hundred a network adapter,
            # but the virtual machine may have more
            net_info = get_vm_net_info(device_moref)
            nets_info.append(net_info)
        else:
            continue
    return (disks_info, nets_info)


def get_vm_disk_info(disk_device, scsi_ctls_type):
    """
    """
    disk_info = {}
    disk_info['label'] = disk_device.deviceInfo.label
    scsi_z1 = old_div((disk_device.key - 2000), 16)
    scsi_z2 = (disk_device.key - 2000) % 16
    # unitNumber 7 reserved for scsi controller
    scsi_z2 += 1 if scsi_z2 >= 7 else 0
    disk_info['scsi_name'] = "SCSI(%d:%d)" % (scsi_z1, scsi_z2)
    disk_info['scsi_type'] = scsi_ctls_type.get(disk_device.controllerKey)
    disk_info['file_name'] = disk_device.backing.fileName
    disk_info['capacityKB'] = disk_device.capacityInKB
    disk_info['disk_mode'] = disk_device.backing.diskMode
    disk_info['uuid'] = disk_device.backing.uuid
    disk_info['contentid'] = disk_device.backing.contentId
    disk_info['ds_name'] = disk_device.backing.datastore.name
    disk_info['ds_moid'] = disk_device.backing.datastore._moId
    if isinstance(disk_device.backing,
                  vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo):
        is_raw_disk = True
        disk_type = 'raw'
    elif isinstance(disk_device.backing,
                    vim.vm.device.VirtualDisk.FlatVer2BackingInfo):
        is_raw_disk = False
        if disk_device.backing.thinProvisioned:
            disk_type = constants.DISK_TYPE_THIN
        elif disk_device.backing.eagerlyScrub:
            disk_type = constants.DISK_TYPE_EAGER_ZEROED_THICK
        else:
            disk_type = constants.DISK_TYPE_PREALLOCATED
    disk_info['disk_type'] = disk_type
    disk_info['is_raw'] = is_raw_disk
    return disk_info


def get_vm_net_info(net_device):
    """
    """
    net_info = {}
    if isinstance(net_device, vim.vm.device.VirtualVmxnet3):
        adapter_type = 'VMXNET3'
    elif isinstance(net_device, vim.vm.device.VirtualE1000):
        adapter_type = 'E1000'
    elif isinstance(net_device, vim.vm.device.VirtualE1000e):
        adapter_type = 'E1000E'
    else:
        adapter_type = ''
    net_info['adapter_type'] = adapter_type
    if isinstance(net_device.backing,
                  vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo):
        pg_type = 'dvs'
        pg_moid = net_device.backing.port.portgroupKey
    elif isinstance(net_device.backing,
                    vim.vm.device.VirtualEthernetCard.NetworkBackingInfo):
        pg_type = 'ovs'
        pg_moid = net_device.backing.network._moId
    else:
        pg_type = ''
        pg_moid = ''
    net_info['pg_type'] = pg_type
    net_info['pg_moid'] = pg_moid
    net_info['portgroup'] = unquote(net_device.deviceInfo.summary)
    net_info['key'] = net_device.key
    net_info['label'] = net_device.deviceInfo.label
    net_info['mac_addr'] = net_device.macAddress
    net_info['connected'] = net_device.connectable.connected
    net_info['ipv4'] = ''
    net_info['prefix'] = ''
    return net_info
