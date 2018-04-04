# -*- coding:utf-8 -*-

"""
@@ function:
"""
from __future__ import absolute_import

import six
import collections
from os.path import basename
from oslo_utils import units
from pyVmomi import vim

import constants

VmdkInfo = collections.namedtuple('VmdkInfo', ['path', 'adapter_type',
                                               'disk_type',
                                               'capacity_in_bytes',
                                               'device'])


def wait_for_task(task):
    """
    wait for a vCenter task to finish.
    """
    while True:
        if task.info.state == 'success':
            return (True, task.info)
        elif task.info.state == 'error':
            return (False, task.info)


def get_vmdk_info(vm_ref, uuid=None):
    """Returns information for the primary VMDK attached to the given VM."""
    vmdk_file_path = None
    vmdk_controller_key = None
    disk_type = None
    capacity_in_bytes = 0

    # Determine if we need to get the details of the root disk
    root_disk = None
    root_device = None
    if uuid:
        root_disk = '%s.vmdk' % uuid
    vmdk_device = None

    adapter_type_dict = {}
    hardware_devices = vm_ref.config.hardware.device
    for device in hardware_devices:
        if device.__class__.__name__ == "vim.vm.device.VirtualDisk":
            if device.backing.__class__.__name__ == "vim.vm.device.VirtualDisk.FlatVer2BackingInfo":
                path = device.backing.fileName
                if root_disk and basename(path) == root_disk:
                    root_device = device
                vmdk_device = device
        elif device.__class__.__name__ == "vim.vm.device.VirtualLsiLogicController":
            adapter_type_dict[device.key] = constants.DEFAULT_ADAPTER_TYPE
        elif device.__class__.__name__ == "vim.vm.device.VirtualBusLogicController":
            adapter_type_dict[device.key] = constants.ADAPTER_TYPE_BUSLOGIC
        elif device.__class__.__name__ == "vim.vm.device.VirtualIDEController":
            adapter_type_dict[device.key] = constants.ADAPTER_TYPE_IDE
        elif device.__class__.__name__ == "vim.vm.device.VirtualLsiLogicSASController":
            adapter_type_dict[device.key] = constants.ADAPTER_TYPE_LSILOGICSAS
        elif device.__class__.__name__ == "vim.vm.device.ParaVirtualSCSIController":
            adapter_type_dict[device.key] = constants.ADAPTER_TYPE_PARAVIRTUAL

    if root_disk:
        vmdk_device = root_device

    if vmdk_device:
        vmdk_file_path = vmdk_device.backing.fileName
        capacity_in_bytes = _get_device_capacity(vmdk_device)
        vmdk_controller_key = vmdk_device.controllerKey
        disk_type = _get_device_disk_type(vmdk_device)

    adapter_type = adapter_type_dict.get(vmdk_controller_key)
    return VmdkInfo(vmdk_file_path, adapter_type, disk_type,
                    capacity_in_bytes, vmdk_device)


def _get_device_capacity(device):
    # Devices pre-vSphere-5.5 only reports capacityInKB, which has
    # rounding inaccuracies. Use that only if the more accurate
    # attribute is absent.
    if hasattr(device, 'capacityInBytes'):
        return device.capacityInBytes
    else:
        return device.capacityInKB * units.Ki


def _get_device_disk_type(device):
    if getattr(device.backing, 'thinProvisioned', False):
        return constants.DISK_TYPE_THIN
    else:
        if getattr(device.backing, 'eagerlyScrub', False):
            return constants.DISK_TYPE_EAGER_ZEROED_THICK
        else:
            return constants.DEFAULT_DISK_TYPE


def _find_allocated_slots(devices):                                                                                                                                                                                                    
    """Return dictionary which maps controller_key to list of allocated unit
    numbers for that controller_key.
    """
    taken = {}
    for device in devices:
        if hasattr(device, 'controllerKey') and hasattr(device, 'unitNumber'):
            unit_numbers = taken.setdefault(device.controllerKey, [])
            unit_numbers.append(device.unitNumber)
        if _is_scsi_controller(device):
            # the SCSI controller sits on its own bus
            unit_numbers = taken.setdefault(device.key, [])
            unit_numbers.append(device.scsiCtlrUnitNumber)
    return taken


def _find_controller_slot(controller_keys, taken, max_unit_number):
    for controller_key in controller_keys:
        for unit_number in range(max_unit_number):
            if unit_number not in taken.get(controller_key, []):
                return controller_key, unit_number


def _is_ide_controller(device):
    return device.__class__.__name__ == 'vim.vm.device.VirtualIDEController'


def _is_scsi_controller(device):
    return device.__class__.__name__ in ['vim.vm.device.VirtualLsiLogicController',
                                         'vim.vm.device.VirtualLsiLogicSASController',
                                         'vim.vm.device.VirtualBusLogicController',
                                         'vim.vm.device.ParaVirtualSCSIController']


def _get_bus_number_for_scsi_controller(devices):
    """Return usable bus number when create new SCSI controller."""
    # Every SCSI controller will take a unique bus number
    taken = [dev.busNumber for dev in devices if _is_scsi_controller(dev)]
    # The max bus number for SCSI controllers is 3
    for i in range(constants.SCSI_MAX_CONTROLLER_NUMBER):
        if i not in taken:
            return i
    msg = _('Only %d SCSI controllers are allowed to be '
            'created on this instance.') % constants.SCSI_MAX_CONTROLLER_NUMBER
    raise vexc.VMwareDriverException(msg)


def allocate_controller_key_and_unit_number(vm_ref,
                                            adapter_type):
    """This function inspects the current set of hardware devices and returns
    controller_key and unit_number that can be used for attaching a new virtual
    disk to adapter with the given adapter_type.
    """
    devices = vm_ref.config.hardware.device

    taken = _find_allocated_slots(devices)

    ret = None
    if adapter_type == constants.ADAPTER_TYPE_IDE:
        ide_keys = [dev.key for dev in devices if _is_ide_controller(dev)]
        ret = _find_controller_slot(ide_keys, taken, 2)
    elif adapter_type in constants.SCSI_ADAPTER_TYPES:
        scsi_keys = [dev.key for dev in devices if _is_scsi_controller(dev)]
        ret = _find_controller_slot(scsi_keys, taken, 16)
    if ret:
        return ret[0], ret[1], None

    # create new controller with the specified type and return its spec
    controller_key = -101

    # Get free bus number for new SCSI controller.
    bus_number = 0
    if adapter_type in constants.SCSI_ADAPTER_TYPES:
        bus_number = _get_bus_number_for_scsi_controller(devices)

    controller_spec = create_controller_spec(controller_key,
                                             adapter_type, bus_number)
    return controller_key, 0, controller_spec


def create_controller_spec(key,
                           adapter_type=constants.DEFAULT_ADAPTER_TYPE,
                           bus_number=0):
    """Builds a Config Spec for the LSI or Bus Logic Controller's addition
    which acts as the controller for the virtual hard disk to be attached
    to the VM.
    """
    # Create a controller for the Virtual Hard Disk
    virtual_device_config = vim.vm.device.VirtualDeviceSpec()
    virtual_device_config.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    if adapter_type == constants.ADAPTER_TYPE_BUSLOGIC:
        virtual_controller = vim.vm.device.VirtualBusLogicController()
    elif adapter_type == constants.ADAPTER_TYPE_LSILOGICSAS:
        virtual_controller = vim.vm.device.ParaVirtualSCSIController()
    elif adapter_type == constants.ADAPTER_TYPE_PARAVIRTUAL:
        virtual_controller = vim.vm.device.ParaVirtualSCSIController()
    else:
        virtual_controller = vim.vm.device.VirtualLsiLogicController()
    virtual_controller.key = key
    virtual_controller.busNumber = bus_number
    virtual_controller.sharedBus = "noSharing"
    virtual_device_config.device = virtual_controller
    return virtual_device_config


def get_vmdk_attach_config_spec(
                                disk_type=constants.DEFAULT_DISK_TYPE,
                                file_path=None,
                                disk_size=None,
                                linked_clone=False,
                                controller_key=None,
                                unit_number=None,
                                device_name=None,
                                disk_io_limits=None):
    """Builds the vmdk attach config spec."""
    create_spec = vim.vm.ConfigSpec()

    device_config_spec = []
    virtual_device_config_spec = _create_virtual_disk_spec(
                                controller_key, disk_type, file_path,
                                disk_size, linked_clone,
                                unit_number, device_name, disk_io_limits)

    device_config_spec.append(virtual_device_config_spec)

    create_spec.deviceChange = device_config_spec
    return create_spec


def _create_virtual_disk_spec(controller_key,
                              disk_type=constants.DEFAULT_DISK_TYPE,
                              file_path=None,
                              disk_size=None,
                              linked_clone=False,
                              unit_number=None,
                              device_name=None,
                              disk_io_limits=None):
    """Builds spec for the creation of a new/ attaching of an already existing
    Virtual Disk to the VM.
    """
    virtual_device_config = vim.vm.device.VirtualDeviceSpec()
    virtual_device_config.operation = "add"
    if (file_path is None) or linked_clone:
        virtual_device_config.fileOperation = "create"

    virtual_disk = vim.vm.device.VirtualDisk()

    if disk_type == "rdm" or disk_type == "rdmp":
        disk_file_backing = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
        disk_file_backing.compatibilityMode = "virtualMode" \
            if disk_type == "rdm" else "physicalMode"
        disk_file_backing.diskMode = "independent_persistent"
        disk_file_backing.deviceName = device_name or ""
    else:
        disk_file_backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_file_backing.diskMode = "persistent"
        if disk_type == constants.DISK_TYPE_THIN:
            disk_file_backing.thinProvisioned = True
        else:
            if disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
                disk_file_backing.eagerlyScrub = True
    disk_file_backing.fileName = file_path or ""

    connectable_spec = vim.vm.device.VirtualDevice.ConnectInfo()
    connectable_spec.startConnected = True
    connectable_spec.allowGuestControl = False
    connectable_spec.connected = True

    if not linked_clone:
        virtual_disk.backing = disk_file_backing
    else:
        virtual_disk.backing = copy.copy(disk_file_backing)
        virtual_disk.backing.fileName = ""
        virtual_disk.backing.parent = disk_file_backing
    virtual_disk.connectable = connectable_spec

    # The Server assigns a Key to the device. Here we pass a -ve random key.
    # -ve because actual keys are +ve numbers and we don't
    # want a clash with the key that server might associate with the device
    virtual_disk.key = -100
    virtual_disk.controllerKey = controller_key
    virtual_disk.unitNumber = unit_number or 0
    virtual_disk.capacityInKB = disk_size or 0

    if disk_io_limits and disk_io_limits.has_limits():
        virtual_disk.storageIOAllocation = _get_allocation_info(
            disk_io_limits,
            vim.StorageResourceManager.IOAllocationInfo)

    virtual_device_config.device = virtual_disk

    return virtual_device_config

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


def get_vmdk_backed_disk_device(hardware_devices, uuid):
    for device in hardware_devices:
        if (device.__class__.__name__ == "vim.vm.device.VirtualDisk" and
                device.backing.__class__.__name__ ==
                "vim.vm.device.VirtualDisk.FlatVer2BackingInfo" and
                device.backing.uuid == uuid):
            return device


def get_vmdk_volume_disk(hardware_devices, path=None):
    for device in hardware_devices:
        if (device.__class__.__name__ == "vim.vm.device.VirtualDisk"):
            if not path or path == device.backing.fileName:
                return device


def relocate_vm_spec(datastore=None, host=None,
                     disk_move_type="moveAllDiskBackingsAndAllowSharing"):
    """Builds the VM relocation spec."""
    rel_spec = vim.vm.RelocateSpec()
    rel_spec.datastore = datastore
    rel_spec.diskMoveType = disk_move_type
    if host:
        rel_spec.host = host
    return rel_spec


def get_vmdk_detach_config_spec(device,
                                destroy_disk=False):
    """Builds the vmdk detach config spec."""
    config_spec = vim.vm.ConfigSpec()

    device_config_spec = []
    virtual_device_config_spec = detach_virtual_disk_spec(device,
                                                          destroy_disk)

    device_config_spec.append(virtual_device_config_spec)

    config_spec.deviceChange = device_config_spec
    return config_spec


def detach_virtual_disk_spec(device, destroy_disk=False):
    """Builds spec for the detach of an already existing Virtual Disk from VM.
    """
    virtual_device_config = vim.vm.device.VirtualDeviceSpec()
    virtual_device_config.operation = "remove"
    if destroy_disk:
        virtual_device_config.fileOperation = "destroy"
    virtual_device_config.device = device

    return virtual_device_config


def reconfigure_vm(vm_ref, config_spec):
    """Reconfigure a VM according to the config spec."""
    reconfig_task =vm_ref.ReconfigVM_Task(spec=config_spec)
    return wait_for_task(reconfig_task)


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


