# -*- coding:utf-8 -*-

"""
@@ function:
@ vm_info_json: get VM details

"""


from pyVmomi import vim


def vm_info_json(vm_obj):
    """
    To json information for a particular virtual machine
    @ vm_obj: vim.VirtualMachine
    """
    vm_details = {}
    summary = vm_obj.summary
    vm_details["name"] = summary.config.name
    vm_details["esxiHost"] = summary.runtime.host.name
    vm_details["path"] = summary.config.vmPathName
    vm_details["guest"] = summary.config.guestFullName
    vm_details["state"] = summary.runtime.powerState
    vm_details["numCpu"] = summary.config.numCpu
    vm_details["memorySizeMB"] = summary.config.memorySizeMB
    vm_details["ip"] = ''
    if summary.guest is not None and summary.guest.ipAddress is not None:
        vm_details["ip"] = summary.guest.ipAddress
    disks_info = disk_info_json(vm_obj.config.hardware.device)
    vm_details['disk'] = disks_info
    vm_details['is_template'] = vm_obj.config.template
    return vm_details


def disk_info_json(virtual_devices):
    """
    To json information for a particular virtual machine disk
    @ virtual_devices: vim.vm.device.VirtualDevice[]
    @@  vim.vm.device.ParaVirtualSCSIController
    @@  vim.vm.device.VirtualCdrom
    @@  vim.vm.device.VirtualDisk
    @@  vim.vm.device.VirtualFloppy
    @@  vim.vm.device.VirtualIDEController
    @@  vim.vm.device.VirtualKeyboard
    @@  vim.vm.device.VirtualPCIController
    @@  vim.vm.device.VirtualPointingDevice
    @@  vim.vm.device.VirtualPS2Controller
    @@  vim.vm.device.VirtualSIOController
    @@  vim.vm.device.VirtualVideoCard
    @@  vim.vm.device.VirtualVMCIDevice
    @@  vim.vm.device.VirtualVmxnet3
    """
    disks_info = []
    for device_obj in virtual_devices:
        if not isinstance(device_obj, vim.vm.device.VirtualDisk):
            continue
        disk_info = {}

        disk_info['label'] = device_obj.deviceInfo.label
        scsi_z1 = (device_obj.key - 2000) / 16
        scsi_z2 = (device_obj.key - 2000) % 16
        disk_info['scsi'] = "SCSI(%d:%d)" % (scsi_z1, scsi_z2)
        disk_info['backingName'] = device_obj.backing.fileName
        disk_info['capacityInKB'] = device_obj.capacityInKB
        disk_info['diskMode'] = device_obj.backing.diskMode
        if isinstance(device_obj.backing,
                      vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo):
            is_raw_disk = True
            disk_type = 'raw'
        elif isinstance(device_obj.backing,
                        vim.vm.device.VirtualDisk.FlatVer2BackingInfo):
            is_raw_disk = False
            if device_obj.backing.thinProvisioned:
                disk_type = 'Thin'
            elif device_obj.backing.eagerlyScrub:
                disk_type = 'EagerZeroedThick'
            else:
                disk_type = 'Thick'
        disk_info['diskType'] = disk_type
        disk_info['isRawDisk'] = is_raw_disk

        disks_info.append(disk_info)

    return disks_info
