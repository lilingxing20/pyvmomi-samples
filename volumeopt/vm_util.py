# -*- coding:utf-8 -*-

"""
"""
from __future__ import absolute_import

import collections
from os.path import basename
from oslo_utils import units

import constants
import spec_util

VmdkInfo = collections.namedtuple('VmdkInfo', ['path', 'adapter_type',
                                               'disk_type',
                                               'capacity_in_bytes',
                                               'device'])


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


def allocate_controller_key_and_unit_number(vm_ref, adapter_type):
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
    if adapter_type in constants.SCSI_ADAPTER_TYPES:
        bus_number = _get_bus_number_for_scsi_controller(devices)

    controller_spec = spec_util.create_controller_add_spec(adapter_type,
                                                           controller_key=controller_key,
                                                           bus_number=0)
    return controller_key, 0, controller_spec


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

