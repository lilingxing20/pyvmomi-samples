#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
Author      : lixx (https://github.com/lilingxing20)
Created Time: Tue 10 Apr 2018 10:40:30 AM CST
File Name   : spec_util.py
Description : 
'''

from pyVmomi import vim

import six

import constants


class VirtualVifModel(object):
    """Supported virtual vif models."""

    VIF_MODEL_PCNET = vim.vm.device.VirtualPCNet32
    VIF_MODEL_E1000 = vim.vm.device.VirtualE1000
    VIF_MODEL_E1000E = vim.vm.device.VirtualE1000e
    VIF_MODEL_SRIOV = vim.vm.device.VirtualSriovEthernetCard
    VIF_MODEL_VMXNET = vim.vm.device.VirtualVmxnet
    VIF_MODEL_VMXNET3 = vim.vm.device.VirtualVmxnet3

    # thick in extra_spec means lazy-zeroed thick disk
    ALL_VIF_MODEL_DICT = {
            'pcnet': VIF_MODEL_PCNET,
            'e1000':  VIF_MODEL_E1000,
            'e1000e':  VIF_MODEL_E1000E,
            'sriov': VIF_MODEL_SRIOV,
            'vmxnet': VIF_MODEL_VMXNET,
            'vmxnet3': VIF_MODEL_VMXNET3,
            }

    @staticmethod
    def is_valid(vif_model):
        """Check if the given vif model in ALL_VIF_MODEL_DICT.keys() is valid.

        :param vif_model: vif model in ALL_VIF_MODEL_DICT.keys()
        :return: True if valid
        """
        return (vif_model in VirtualVifModel.ALL_VIF_MODEL_DICT)

    @staticmethod
    def validate(vif_model):
        """Validate the given vif_model in ALL_VIF_MODEL_DICT.keys().

        This method throws an instance of InvalidVifModelException if the given
        vif model is invalid.

        :param vif_model: vif model in ALL_VIF_MODEL_DICT.keys()
        :raises: InvalidVifModelException
        """
        if not VirtualVifModel.is_valid(vif_model):
            raise vmdk_exceptions.InvalidVifModelException(vif_model=vif_model)

    @staticmethod
    def get_virtual_vif_model(vif_model):
        """Return vif model class corresponding to the extra_spec vif model.

        :param vif_model: vif model in ALL_VIF_MODEL_DICT.keys()
        :return: virtual vif model class
        :raises: InvalidVifModelException
        """
        VirtualVifModel.validate(vif_model)
        return (VirtualVifModel.ALL_VIF_MODEL_DICT[vif_model])


class VirtualDiskType(object):
    """Supported virtual disk types."""

    EAGER_ZEROED_THICK = "eagerZeroedThick"
    PREALLOCATED = "preallocated"
    THIN = "thin"

    # thick in extra_spec means lazy-zeroed thick disk
    EXTRA_SPEC_DISK_TYPE_DICT = {'eagerZeroedThick': EAGER_ZEROED_THICK,
                                 'thick': PREALLOCATED,
                                 'thin': THIN
                                 }

    @staticmethod
    def is_valid(extra_spec_disk_type):
        """Check if the given disk type in extra_spec is valid.

        :param extra_spec_disk_type: disk type in extra_spec
        :return: True if valid
        """
        return (extra_spec_disk_type in
                VirtualDiskType.EXTRA_SPEC_DISK_TYPE_DICT)

    @staticmethod
    def validate(extra_spec_disk_type):
        """Validate the given disk type in extra_spec.

        This method throws an instance of InvalidDiskTypeException if the given
        disk type is invalid.

        :param extra_spec_disk_type: disk type in extra_spec
        :raises: InvalidDiskTypeException
        """
        if not VirtualDiskType.is_valid(extra_spec_disk_type):
            raise vmdk_exceptions.InvalidDiskTypeException(
                disk_type=extra_spec_disk_type)

    @staticmethod
    def get_virtual_disk_type(extra_spec_disk_type):
        """Return disk type corresponding to the extra_spec disk type.

        :param extra_spec_disk_type: disk type in extra_spec
        :return: virtual disk type
        :raises: InvalidDiskTypeException
        """
        VirtualDiskType.validate(extra_spec_disk_type)
        return (VirtualDiskType.EXTRA_SPEC_DISK_TYPE_DICT[
                extra_spec_disk_type])


class VirtualDiskAdapterType(object):
    """Supported virtual disk adapter types."""

    LSI_LOGIC = "lsiLogic"
    BUS_LOGIC = "busLogic"
    LSI_LOGIC_SAS = "lsiLogicsas"
    PARA_VIRTUAL = "paraVirtual"
    IDE = "ide"

    @staticmethod
    def is_valid(adapter_type):
        """Check if the given adapter type is valid.

        :param adapter_type: adapter type to check
        :return: True if valid
        """
        return adapter_type in [VirtualDiskAdapterType.LSI_LOGIC,
                                VirtualDiskAdapterType.BUS_LOGIC,
                                VirtualDiskAdapterType.LSI_LOGIC_SAS,
                                VirtualDiskAdapterType.PARA_VIRTUAL,
                                VirtualDiskAdapterType.IDE]

    @staticmethod
    def validate(extra_spec_adapter_type):
        """Validate the given adapter type in extra_spec.

        This method throws an instance of InvalidAdapterTypeException if the
        given adapter type is invalid.

        :param extra_spec_adapter_type: adapter type in extra_spec
        :raises: InvalidAdapterTypeException
        """
        if not VirtualDiskAdapterType.is_valid(extra_spec_adapter_type):
            raise vmdk_exceptions.InvalidAdapterTypeException(
                invalid_type=extra_spec_adapter_type)

    @staticmethod
    def get_adapter_type(extra_spec_adapter):
        """Get the adapter type to be used in VirtualDiskSpec.

        :param extra_spec_adapter: adapter type in the extra_spec
        :return: adapter type to be used in VirtualDiskSpec
        """
        VirtualDiskAdapterType.validate(extra_spec_adapter)
        # We set the adapter type as lsiLogic for lsiLogicsas/paraVirtual
        # since it is not supported by VirtualDiskManager APIs. This won't
        # be a problem because we attach the virtual disk to the correct
        # controller type and the disk adapter type is always resolved using
        # its controller key.
        if (extra_spec_adapter == VirtualDiskAdapterType.LSI_LOGIC_SAS or
                extra_spec_adapter == VirtualDiskAdapterType.PARA_VIRTUAL):
            return VirtualDiskAdapterType.LSI_LOGIC
        else:
            return extra_spec_adapter


class ControllerType(object):
    """Encapsulate various controller types."""

    LSI_LOGIC = vim.vm.device.VirtualLsiLogicController
    BUS_LOGIC = vim.vm.device.VirtualBusLogicController
    LSI_LOGIC_SAS = vim.vm.device.VirtualLsiLogicSASController
    PARA_VIRTUAL = vim.vm.device.ParaVirtualSCSIController
    IDE = vim.vm.device.VirtualIDEController

    CONTROLLER_TYPE_DICT = {
        VirtualDiskAdapterType.LSI_LOGIC: LSI_LOGIC,
        VirtualDiskAdapterType.BUS_LOGIC: BUS_LOGIC,
        VirtualDiskAdapterType.LSI_LOGIC_SAS: LSI_LOGIC_SAS,
        VirtualDiskAdapterType.PARA_VIRTUAL: PARA_VIRTUAL,
        VirtualDiskAdapterType.IDE: IDE}

    @staticmethod
    def get_controller_type(adapter_type):
        """Get the disk controller type based on the given adapter type.

        :param adapter_type: disk adapter type
        :return: controller type corresponding to the given adapter type
        :raises: InvalidAdapterTypeException
        """
        if adapter_type in ControllerType.CONTROLLER_TYPE_DICT:
            return ControllerType.CONTROLLER_TYPE_DICT[adapter_type]
        raise vmdk_exceptions.InvalidAdapterTypeException(
            invalid_type=adapter_type)

    @staticmethod
    def is_scsi_controller(controller_type):
        """Check if the given controller is a SCSI controller.

        :param controller_type: controller type
        :return: True if the controller is a SCSI controller
        """
        return controller_type in [ControllerType.LSI_LOGIC,
                                   ControllerType.BUS_LOGIC,
                                   ControllerType.LSI_LOGIC_SAS,
                                   ControllerType.PARA_VIRTUAL]

def create_controller_add_spec(adapter_type, controller_key=-100, bus_number=0, sharing='noSharing'):
    """Returns config spec for adding a disk controller.
       :param adapter_type: busLogic | lsiLogic | lsiLogicsas | paraVirtual | ide
       :param sharing: virtualSharing | noSharing | physicalSharing
    """
    controller_type = ControllerType.get_controller_type(adapter_type)
    controller_device = controller_type()
    controller_device.key = controller_key
    controller_device.busNumber = bus_number
    if ControllerType.is_scsi_controller(controller_type):
        controller_device.sharedBus = sharing

    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.operation = 'add'
    controller_spec.device = controller_device
    return controller_spec


def create_controller_edit_spec(controller_device, sharing='noSharing'):
    """Returns config spec for operating a disk controller.
       :param controller_device: 
       :param sharing: virtualSharing | noSharing | physicalSharing
    """
    if controller_device:
        controller_type = controller_device.__class__.__name__
    else:
        controller_type = None
    if ControllerType.is_scsi_controller(controller_type):
        controller_device.sharedBus = sharing

    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.operation = 'edit'
    controller_spec.device = controller_device
    return controller_spec


def create_controller_del_spec(controller_device=None):
    """Returns config spec for operating a disk controller.
       :param controller_device: 
    """
    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.operation = 'remove'
    controller_spec.device = controller_device
    return controller_spec


def _create_disk_backing(disk_type, vmdk_path, disk_uuid=None, device_name=None):
    """Creates file backing for virtual disk.
       :param disk_type: thin | preallocated | eagerZeroedThick
    """
    if disk_type in ['rdm', 'rdmp']:
        disk_device_bkng = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
        disk_device_bkng.compatibilityMode = "virtualMode" \
                if disk_type == "rdm" else "physicalMode"
        disk_file_backing.diskMode = "independent_persistent"
        disk_file_backing.deviceName = device_name or ""
    else:
        disk_device_bkng = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_device_bkng.diskMode = 'persistent'
        if disk_type == VirtualDiskType.EAGER_ZEROED_THICK:
            disk_device_bkng.eagerlyScrub = True
        elif disk_type == VirtualDiskType.THIN:
            disk_device_bkng.thinProvisioned = True
        elif disk_type == VirtualDiskType.PREALLOCATED:
            disk_device_bkng.thinProvisioned =  False
    disk_device_bkng.fileName = vmdk_path or ''
    disk_device_bkng.uuid = disk_uuid or ''

    return disk_device_bkng


def _edit_disk_backing(disk_device_bkng, disk_type, vmdk_path):
    """Creates file backing for virtual disk.
       :param disk_type: thin | preallocated | eagerZeroedThick
    """
    if disk_type == VirtualDiskType.EAGER_ZEROED_THICK:
        disk_device_bkng.eagerlyScrub = True
    elif disk_type == VirtualDiskType.THIN:
        disk_device_bkng.thinProvisioned = True
    elif disk_type == VirtualDiskType.PREALLOCATED:
        disk_device_bkng.thinProvisioned =  False
    disk_device_bkng.fileName = vmdk_path or ''

    return disk_device_bkng


def _create_profile_spec(profile_id):
    """Create the vm profile spec configured for storage policy."""
    storage_profile_spec = vim.vm.DefinedProfileSpec()
    storage_profile_spec.profileId = profile_id.uniqueId
    return storage_profile_spec


def _get_allocation_info(limits, allocation_type):
    allocation = allocation_type()
    if limits.limit:
        allocation.limit = limits.limit
    else:
        # Set as 'unlimited'
        allocation.limit = -1
    if limits.reservation:
        allocation.reservation = limits.reservation
    else:
        allocation.reservation = 0
    shares = vim.SharesInfo()
    if limits.shares_level:
        shares.level = limits.shares_level
        if (shares.level == 'custom' and
            limits.shares_share):
            shares.shares = limits.shares_share
        else:
            shares.shares = 0
    else:
        shares.level = 'normal'
        shares.shares = 0
    # The VirtualEthernetCardResourceAllocation has 'share' instead of
    # 'shares'.
    if hasattr(allocation, 'share'):
        allocation.share = shares
    else:
        allocation.shares = shares
    return allocation


def create_disk_spec_for_add(controller_key, disk_type, size_kb,
                             profile_id=None,
                             vmdk_path=None,
                             disk_uuid=None,
                             unit_number=None,
                             linked_clone=False,
                             disk_io_limits=None):
    """Returns config spec for operating a virtual disk."""

    disk_device = vim.vm.device.VirtualDisk()
    disk_device.key = -100
    disk_device.controllerKey = controller_key
    disk_device.unitNumber = unit_number or 0
    disk_device.capacityInKB = size_kb or 0

    disk_file_backing = _create_disk_backing(disk_type,
                                             vmdk_path,
                                             disk_uuid)
    if not linked_clone:
        disk_device.backing = disk_file_backing
    else:
        disk_device.backing = copy.copy(disk_file_backing)
        disk_device.backing.fileName = ''
        disk_device.backing.parent = disk_file_backing

    connectable_spec = vim.vm.device.VirtualDevice.ConnectInfo()
    connectable_spec.startConnected = True
    connectable_spec.allowGuestControl = False
    connectable_spec.connected = True
    disk_device.connectable = connectable_spec

    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = 'add'
    if (vmdk_path is None) or linked_clone:
        device_spec.fileOperation = 'create'

    if disk_io_limits and disk_io_limits.has_limits():
        disk_device.storageIOAllocation = _get_allocation_info(
                disk_io_limits,
                vim.StorageResourceManager.IOAllocationInfo)

    device_spec.device = disk_device
    if profile_id:
        disk_profile = _create_profile_spec(profile_id)
        device_spec.profile = [disk_profile]

    return device_spec


def create_disk_spec_for_edit(device, disk_type, size_kb,
                              vmdk_path=None,
                              profile_id=None,
                              linked_clone=False):
    """Returns config spec for operating a virtual disk."""
    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = 'edit'
    device_spec.device = device
    device_spec.device.capacityInKB = size_kb or 0

    device_spec.device.backing = _edit_disk_backing(device.backing, disk_type,
                                                    vmdk_path)

    return device_spec


def create_spec_for_disk_remove(device, destroy_disk=True):
    """Builds spec for the detach of an already existing Virtual Disk from VM.
    """
    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = 'remove'
    device_spec.device = device
    if destroy_disk:
        device_spec.fileOperation = 'destroy'
    return device_spec


def create_specs_for_disk_add(size_kb, disk_type, adapter_type,
                              profile_id=None,
                              vmdk_path=None,
                              disk_uuid=None):
    """Create controller and disk config specs for adding a new disk.

    :param size_kb: disk size in KB
    :param disk_type: disk provisioning type
    :param adapter_type: disk adapter type
    :param profile_id: storage policy profile identification
    :param vmdk_path: Optional datastore file path of an existing
                              virtual disk. If specified, file backing is
                              not created for the virtual disk.
    :return: list containing controller and disk config specs
    """
    controller_spec = None
    if adapter_type == 'ide':
        # For IDE disks, use one of the default IDE controllers (with keys
        # 200 and 201) created as part of backing VM creation.
        controller_key = 200
    else:
        controller_spec = create_controller_add_spec(adapter_type)
        controller_key = controller_spec.device.key

    disk_spec = create_disk_spec_for_add(controller_key,
                                         disk_type,
                                         size_kb,
                                         profile_id,
                                         vmdk_path,
                                         disk_uuid)
    specs = [disk_spec]
    if controller_spec is not None:
        specs.append(controller_spec)
    return specs


def _create_vif_spec(vif_info, vif_limits=None):
    """Builds a config spec for the addition of a new network
    adapter to the VM.
    """
    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = "add"

    # Keep compatible with other Hyper vif model parameter.
    vif_model = VirtualVifModel.get_virtual_vif_model(vif_info['vif_model'])
    net_device = vif_model()

    # NOTE(asomya): Only works on ESXi if the portgroup binding is set to
    # ephemeral. Invalid configuration if set to static and the NIC does
    # not come up on boot if set to dynamic.
    network_type = vif_info['network_type']
    backing = None
    if network_type == "DistributedVirtualPortgroup":
        backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        portgroup = vim.dvs.PortConnection()
        portgroup.switchUuid = vif_info['dvpg_uuid']
        portgroup.portgroupKey = vif_info['dvpg_moid']
        if vif_info.get('dvs_port_key'):
            portgroup.portKey = vif_info['dvs_port_key']
        backing.port = portgroup
    elif network_type == "Network":
        backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        backing.deviceName = vif_info['network_name']
    else:
        raise vmdk_exceptions.InvalidNetworkTypeException(
            invalid_type=network_type)

    connectable_spec = vim.vm.device.VirtualDevice.ConnectInfo()
    connectable_spec.startConnected = True
    connectable_spec.allowGuestControl = True
    connectable_spec.connected = True

    net_device.connectable = connectable_spec
    net_device.backing = backing

    # The Server assigns a Key to the device. Here we pass a -ve temporary key.
    # -ve because actual keys are +ve numbers and we don't
    # want a clash with the key that server might associate with the device
    net_device.key = -47
    net_device.addressType = "manual"
    net_device.macAddress = vif_info['mac_address']
    net_device.wakeOnLanEnabled = True

#    # vnic limits are only supported from version 6.0
#    if vif_limits and vif_limits.has_limits():
#        if hasattr(net_device, 'resourceAllocation'):
#            net_device.resourceAllocation = _get_allocation_info(
#                client_factory, vif_limits,
#                'ns0:VirtualEthernetCardResourceAllocation')
#        else:
#            msg = _('Limits only supported from vCenter 6.0 and above')
#            raise exception.Invalid(msg)

    device_spec.device = net_device
    return device_spec


def _get_extra_config_option_values(self, extra_config):
    option_values = []
    for key, value in extra_config.items():
        opt = vim.option.OptionValue()
        opt.key = key
        opt.value = value
        option_values.append(opt)

    return option_values


def create_vm_config_spec(name, uuid, vcpus, memory_mb, data_store_name,
                          vif_infos,
                          cores_per_socket=None,
                          hw_version=None,
                          vif_limits=None,
                          os_type=constants.DEFAULT_OS_TYPE,
                          profile_id=None,
                          description=None):
    """Builds the VM Create spec."""
    config_spec = vim.vm.ConfigSpec()
    config_spec.name = name
    config_spec.guestId = os_type
    # The name is the unique identifier for the VM.
    config_spec.uuid = uuid
    config_spec.annotation = description or ''
    # Set the hardware version to a compatible version supported by
    # vSphere 5.0. This will ensure that the backing VM can be migrated
    # without any incompatibility issues in a mixed cluster of ESX hosts
    # with versions 5.0 or above.
    config_spec.version = hw_version or 'vmx-08'

    # Allow nested hypervisor instances to host 64 bit VMs.
    if os_type in ("vmkernel5Guest", "vmkernel6Guest", "vmkernel65Guest",
                   "windowsHyperVGuest"):
        config_spec.nestedHVEnabled = "True"

    # Append the profile spec
    if profile_id:
        profile_spec = _create_profile_spec(profile_id)
        config_spec.vmProfile = [profile_spec]

    vm_file_info = vim.vm.FileInfo()
    vm_file_info.vmPathName = "[" + data_store_name + "]"
    config_spec.files = vm_file_info

    tools_info = vim.vm.ToolsConfigInfo()
    tools_info.afterPowerOn = True
    tools_info.afterResume = True
    tools_info.beforeGuestStandby = True
    tools_info.beforeGuestShutdown = True
    tools_info.beforeGuestReboot = True
    config_spec.tools = tools_info

    config_spec.numCPUs = int(vcpus)
    if cores_per_socket:
        config_spec.numCoresPerSocket = int(cores_per_socket)
    config_spec.memoryMB = int(memory_mb)

#    # Configure cpu information
#    if extra_specs.cpu_limits.has_limits():
#        config_spec.cpuAllocation = _get_allocation_info(
#            client_factory, extra_specs.cpu_limits,
#            'ns0:ResourceAllocationInfo')
#    # Configure memory information
#    if extra_specs.memory_limits.has_limits():
#        config_spec.memoryAllocation = _get_allocation_info(
#            client_factory, extra_specs.memory_limits,
#            'ns0:ResourceAllocationInfo')

    devices = []
    for vif_info in vif_infos:
        vif_spec = _create_vif_spec(vif_info, vif_limits)
        devices.append(vif_spec)

#    serial_port_spec = create_serial_port_spec(client_factory)
#    if serial_port_spec:
#        devices.append(serial_port_spec)

    config_spec.deviceChange = devices

    extra_config = []
    # add vm-uuid and iface-id.x values for Neutron
    opt = vim.option.OptionValue()
    opt.key = "nvp.vm-uuid"
    opt.value = uuid
    extra_config.append(opt)

#    # enable to provide info needed by udev to generate /dev/disk/by-id
#    opt = vim.option.OptionValue()
#    opt.key = 'disk.EnableUUID'
#    opt.value = True
#    extra_config.append(opt)

    port_index = 0
    for vif_info in vif_infos:
        if vif_info['iface_id']:
            opt = vim.option.OptionValue()
            opt.key = "nvp.iface-id.%d" % port_index
            opt.value = vif_info['iface_id']
            extra_config.append(opt)
            port_index += 1

#    if (CONF.vmware.console_delay_seconds and
#        CONF.vmware.console_delay_seconds > 0):
#        opt = vim.option.OptionValue()
#        opt.key = 'keyboard.typematicMinDelay'
#        opt.value = CONF.vmware.console_delay_seconds * 1000000
#        extra_config.append(opt)

    config_spec.extraConfig = extra_config

    return config_spec


def create_volume_config_spec(name, uuid, data_store_name,
                              size_kb, disk_type, adapter_type,
                              hw_version=None,
                              profile_id=None,
                              description=None):
    """Builds the VM Create spec."""
    config_spec = vim.vm.ConfigSpec()
    config_spec.name = name
    config_spec.guestId = 'otherGuest'
    config_spec.numCPUs = 1
    config_spec.memoryMB = 128
    # The name is the unique identifier for the VM.
    config_spec.uuid = uuid
    config_spec.annotation = description or ''
    # Set the hardware version to a compatible version supported by
    # vSphere 5.0. This will ensure that the backing VM can be migrated
    # without any incompatibility issues in a mixed cluster of ESX hosts
    # with versions 5.0 or above.
    config_spec.version = hw_version or 'vmx-08'

    # Append the profile spec
    if profile_id:
        profile_spec = _create_profile_spec(profile_id)
        config_spec.vmProfile = [profile_spec]

    vm_file_info = vim.vm.FileInfo()
    vm_file_info.vmPathName = "[" + data_store_name + "]"
    config_spec.files = vm_file_info

    devices = []
    disk_spec = create_specs_for_disk_add(size_kb, disk_type, adapter_type,
                                          profile_id=profile_id,
                                          vmdk_path=None,
                                          disk_uuid=uuid)
    if disk_spec:
        devices += disk_spec
    config_spec.deviceChange = devices

    extra_config = []
    opt = vim.option.OptionValue()
    opt.key = "volume.id"
    opt.value = uuid
    extra_config.append(opt)

    config_spec.extraConfig = extra_config

    return config_spec


def get_vmdk_attach_config_spec(disk_type=constants.DEFAULT_DISK_TYPE,
                                vmdk_path=None,
                                disk_size=None,
                                linked_clone=False,
                                controller_key=None,
                                unit_number=None,
                                device_name=None,
                                disk_uuid=None,
                                disk_io_limits=None):
    """Builds the vmdk attach config spec."""
    create_spec = vim.vm.ConfigSpec()
    device_config_spec = []
    virtual_device_config_spec = create_disk_spec_for_add(controller_key,
                                                          disk_type,
                                                          disk_size,
                                                          vmdk_path=vmdk_path,
                                                          disk_uuid=disk_uuid,
                                                          unit_number=unit_number,
                                                          linked_clone=linked_clone,
                                                          disk_io_limits=disk_io_limits)
    device_config_spec.append(virtual_device_config_spec)
    create_spec.deviceChange = device_config_spec
    return create_spec


def get_vmdk_detach_config_spec(device, destroy_disk=False):
    """Builds the vmdk detach config spec."""
    config_spec = vim.vm.ConfigSpec()
    device_config_spec = []
    virtual_device_config_spec = create_spec_for_disk_remove(device,
                                                             destroy_disk)
    device_config_spec.append(virtual_device_config_spec)
    config_spec.deviceChange = device_config_spec
    return config_spec


def relocate_vm_spec(datastore=None, host=None,
                     disk_move_type="moveAllDiskBackingsAndAllowSharing"):
    """Builds the VM relocation spec."""
    rel_spec = vim.vm.RelocateSpec()
    rel_spec.datastore = datastore
    rel_spec.diskMoveType = disk_move_type
    if host:
        rel_spec.host = host
    return rel_spec


def get_vm_extra_config_spec(extra_opts):
    """Builds extra spec fields from a dictionary."""
    config_spec = vim.vm.ConfigSpec()
    # add the key value pairs
    extra_config = []
    for key, value in six.iteritems(extra_opts):
        opt = vim.option.OptionValue()
        opt.key = key
        opt.value = value
        extra_config.append(opt)
        config_spec.extraConfig = extra_config
    return config_spec



