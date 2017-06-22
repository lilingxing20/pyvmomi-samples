#!/usr/bin/env python
# coding=utf-8

'''
Author      : lixx (https://github.com/lilingxing20)
Created Time: Wed 21 Jun 2017 01:35:28 PM CST
File Name   : op_vm_network.py
Description : 
'''


def add_nic(network_mo, nic_type):
    """
    NIC card add
    :param network_mo: Network Object
    :param nic_type: Network Interface Card  Type
     win2012: VMXNET3, E1000E, E1000
     win2008: VMXNET3, VMXNET2(增强型), E1000
     rhel7: VMXNET3, E1000E, E1000
     rhel6: VMXNET3, E1000
     centos4/5/6/7: VMXNET3, VMXNET2(增强型), E1000
    """

    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

    if nic_type == 'E1000'
        nic_spec.device = vim.vm.device.VirtualE1000()
    elif nic_type == 'E1000E'
        nic_spec.device = vim.vm.device.VirtualE1000e()
    else:
        # nic_type = 'VMXNET3'
        nic_spec.device = vim.vm.device.VirtualVmxnet3()

    nic_spec.device.deviceInfo = vim.Description()
    nic_spec.device.deviceInfo.summary = 'vCenter API test'

    if not isinstance(network_mo, vim.dvs.DistributedVirtualPortgroup):
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.network = network_mo
        nic_spec.device.backing.deviceName = network_mo.name
    else:
        dvs_port_connection = vim.dvs.PortConnection()
        dvs_port_connection.portgroupKey = network_mo.key
        dvs_port_connection.switchUuid = network_mo.config.distributedVirtualSwitch.uuid
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic_spec.device.backing.port = dvs_port_connection
    nic_spec.device.backing.useAutoDetect = False

    nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.allowGuestControl = True
    nic_spec.device.connectable.connected = False
    nic_spec.device.connectable.status = 'untried'
    nic_spec.device.wakeOnLanEnabled = True
    nic_spec.device.addressType = 'assigned'

    return nic_spec




def update_nic_network(nic_mo, network_mo):
    """
    change the network of the Virtual Machine NIC
    :param nic_mo: Virtual Machine NIC device Object
    :param network_mo: Network Object
    """
    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    nic_spec.device = nic_mo

    if not isinstance(network_mo, vim.dvs.DistributedVirtualPortgroup):
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.network = network_mo
        nic_spec.device.backing.deviceName = network_mo.name
    else:
        dvs_port_connection = vim.dvs.PortConnection()
        dvs_port_connection.portgroupKey = network_mo.key
        dvs_port_connection.switchUuid = network_mo.config.distributedVirtualSwitch.uuid
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic_spec.device.backing.port = dvs_port_connection

    nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.startConnected = True
    nic_spec.device.connectable.allowGuestControl = True
    nic_spec.device.connectable.connected = False
    nic_spec.device.connectable.status = 'untried'
    nic_spec.device.wakeOnLanEnabled = True
    nic_spec.device.addressType = 'assigned'

    return nic_spec


def update_vm_nic_network(content, vm_mo, network_mo):
    """
    """
    config_spec = vim.vm.ConfigSpec()

    ## update nic network
    nic_changes = []
    for device in vm_mo.config.hardware.device:
        if not isinstance(device, vim.vm.device.VirtualEthernetCard):
            continue
        nic_spec = update_nic_network(device, network_mo)
        nic_changes.append(nic_spec)

    ## add nic network
    nic_spec = add_nic(network_mo, 'VMXNET3')
    nic_changes.append(nic_spec)

    config_spec.deviceChange = nic_changes
    task = vm.ReconfigVM_Task(config_spec)
    return task

