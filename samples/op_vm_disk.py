#!/usr/bin/env python
# coding=utf-8

'''
Author      : lixx (https://github.com/lilingxing20)
Created Time: Thu 22 Jun 2017 02:46:17 PM CST
File Name   : op_vm_disk.py
Description : 
'''

import constants


def get_usable_disk_unit_number(vm_mo, bus_num=None, unit_num=None):
    """
    get usable scsi controller busNumber, and disk unitNumber
    :param vm_mo: vim.VirtualMachine Object
    :param bus_num: scsi controller bus number [0-3]
    :param unit_num: disk unit number [0-6,8-15]
    """
    usable_bus_num = bus_num
    usable_unit_num = unit_num
    bus_unit_nums = {"1000": [], "1001": [], "1002": [], "1003": []}
    for dev in vm_mo.config.hardware.device:
        # get disk unitNumber
        ## if hasattr(dev.backing, 'fileName'):
        if isinstance(dev, vim.vm.device.VirtualDisk):
            bus_unit_nums[dev.key].append(dev.unitNumber)
    # set unit_number to the next available
    usable_unit_numbers = None
    if usable_bus_num:
        unit_nums = bus_unit_nums.get(str(usable_bus_num + 1000))
    if unit_nums:
        unit_nums.sort()
        usable_unit_numbers = [ i for i in xrange(16) if ii != unit_nums[i] ]
    if usable_unit_numbers is None:
        for bus_key in bus_unit_nums:
            unit_nums = bus_unit_nums[bus_key]
            unit_nums.sort()
            usable_unit_numbers = [ i for i in xrange(16) if ii != unit_nums[i] ]
            if usable_unit_numbers is not None:
                break
    if usable_unit_numbers is None:
        print "Vcenter virtual machine don 't support more disks"
        return
    # unit_number 7 reserved for scsi controller
    usable_unit_numbers.remove(7)
    if usable_unit_num and usable_unit_num not in usable_unit_numbers:
        usable_unit_num = usable_unit_numbers[0]
    return (usable_bus_num, usable_unit_num)


def add_disk(vm_mo, disk_size, disk_type, bus_num=None, unit_num=None):
    """
    add disk for vm
    :param vm_mo: vim.VirtualMachine Object
    :param disk_size: disk size (GB)
    :param disk_type: 
    :param bus_num: scsi controller bus number [0-3]
    :param unit_num: disk unit number [0-6,8-15]
    """
    config_spec = vim.vm.ConfigSpec()
    # get all disks on a VM
    (usable_bus_num, usable_unit_num) = get_usable_disk_unit_number(bus_num, unit_num)
    if not usable_bus_num or not usable_unit_num:
        print "Vcenter virtual machine don 't support more disks"
        return

    scsi_controller = None
    pci_controller = None
    ## scsi controller 0 unitNumber=3
    usable_scsi_unit_num = 4
    for dev in vm_mo.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualPCIController):
            pci_controller = dev
        # get scsi controller object
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            if dev.busNumber == usable_bus_num:
                scsi_controller = dev
                break
            if dev.unitNumber == usable_scsi_unit_num:
                usable_scsi_unit_num += 1
    if scsi_controller is None:
        scsi_controller = vim.vm.device.ParaVirtualSCSIController()
        scsi_controller.key = 1000 + usable_bus_num
        scsi_controller.controllerKey = pci_controller.key
        scsi_controller.unitNumber = usable_scsi_unit_num
        scsi_controller.busNumber = usable_bus_num
        scsi_controller.hotAddRemove = true
        scsi_controller.sharedBus = 'noSharing'
        scsi_controller.scsiCtlrUnitNumber = 7

    # add disk here
    dev_changes = []
    new_disk_kb = int(disk_size) * 1024 * 1024
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = \
        vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    if disk_type == constants.DISK_TYPE_THIN:
        disk_spec.device.backing.thinProvisioned = True
    elif disk_type == constants.DISK_TYPE_PREALLOCATED:
        disk_spec.device.backing.thinProvisioned = False
    elif disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
        disk_spec.device.backing.eagerlyScrub = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = new_disk_kb
    disk_spec.device.controllerKey = scsi_controller.key
    dev_changes.append(disk_spec)
    config_spec.deviceChange = dev_changes
    task = vm_mo.ReconfigVM_Task(spec=config_spec)
    print "%sGB disk added to %s" % (disk_size, vm.config.name)
    return task


def edit_disk(vm_mo, disk_size, disk_type, bus_num=None, unit_num=None):
    """
    """
    config_spec = vim.vm.ConfigSpec()
    dev_changes = []
    disk_label_end = " " + str(disk_label)
    for dev in vm_mo.config.hardware.device:
        if not isinstance(dev, vim.vm.device.VirtualDisk):
            continue
        if not dev.deviceInfo.label.endswith(disk_label_end):
            continue
        # edit disk type
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        disk_spec.device = dev
        if disk_type:
            if disk_type == constants.DISK_TYPE_THIN:
                # disk_spec.device.backing.eagerlyScrub = None
                disk_spec.device.backing.thinProvisioned = True
            elif disk_type == constants.DISK_TYPE_PREALLOCATED:
                # disk_spec.device.backing.eagerlyScrub = False
                disk_spec.device.backing.thinProvisioned = False
            elif disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
                disk_spec.device.backing.eagerlyScrub = True
                # disk_spec.device.backing.thinProvisioned = False
        # else:
        #     LOG.info('The same as the virtual machine template source format.')

        # edit disk size
        new_disk_kb = int(disk_size) * 1024 * 1024
        if disk_spec.device.capacityInKB < new_disk_kb:
            disk_spec.device.capacityInKB = new_disk_kb
        dev_changes.append(disk_spec)
        break

    config_spec.deviceChange = dev_changes
    task = vm.ReconfigVM_Task(spec=config_spec)
    return task
