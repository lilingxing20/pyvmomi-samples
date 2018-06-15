# -*- coding:utf-8 -*-

"""
@@ function:
@ vm_info_json: get VM details

"""
from __future__ import absolute_import, division

import re
import six
import logging
from builtins import str
from pyVmomi import vim

from . import constants, utils


LOG = logging.getLogger(__name__)


def filter_vm_hostname(vm_name, hostname):
    """
    1. Host name only allowed to contain the ASCII character [0-9a-zA-Z-].
    Other are not allowed.
    2. The beginning and end character not allowed is the '-'.
    3. It is strongly recommended that do not use Numbers at the beginning,
    though it is not mandatory

    """
    if not hostname:
        hostname = vm_name
    if not re.match(r'^[a-zA-Z][a-zA-Z\d-]*[a-zA-Z\d]$', hostname):
        hostname = 'localhost'
    return hostname


def sanitize_hostname(vm_name, hostname, default_name='localhost'):
    """Return a hostname which conforms to RFC-952 and RFC-1123 specs except
       the length of hostname.

       Window, Linux, and Dnsmasq has different limitation:

       Windows: 255 (net_bios limits to 15, but window will truncate it)
       Linux: 64
       Dnsmasq: 63

       Due to nova-network will leverage dnsmasq to set hostname, so we chose
       63.

       """

    def truncate_hostname(name):
        # if len(name) > 63:
        #     LOG.warning(_LW("Hostname %(hostname)s is longer than 63, "
        #                     "truncate it to %(truncated_name)s"),
        #                     {'hostname': name, 'truncated_name': name[:63]})
        return name[:63]

    if not hostname:
        hostname = vm_name
    if isinstance(hostname, six.text_type):
        # Remove characters outside the Unicode range U+0000-U+00FF
        hostname = hostname.encode('latin-1', 'ignore')
        if six.PY3:
            hostname = hostname.decode('latin-1')

    hostname = truncate_hostname(hostname)
    hostname = re.sub('[ _]', '-', hostname)
    hostname = re.sub('[^\w.-]+', '', hostname)
    hostname = hostname.upper()
    hostname = hostname.strip('.-')
    # NOTE(eliqiao): set hostname to default_display_name to avoid
    # empty hostname
    if hostname == "" and default_name is not None:
        return truncate_hostname(default_name)
    return hostname


def network_customization(vm_net):
    """
    VM network setting
    vm_net: [
            {'ip': '10.0.0.13', 'netmask': '255.255.255.0', 'gateway': '10.0.0.1'},
            }
    """
    adaptermap_custom = []
    for net in vm_net:
        adaptermap = vim.vm.customization.AdapterMapping()
        if net:
            fixedip = vim.vm.customization.FixedIp(ipAddress=net.get('ip'))
            adaptermap.adapter = vim.vm.customization.IPSettings(ip=fixedip,
                                                                 subnetMask=net.get('netmask'),
                                                                 gateway=net.get('gateway'))
        else:
            dhcpip = vim.vm.customization.DhcpIpGenerator()
            adaptermap.adapter = vim.vm.customization.IPSettings(ip=dhcpip)
        adaptermap_custom.append(adaptermap)
    return adaptermap_custom


def dns_customization(dnslist):
    """
    dnslist = ['10.1.10.14', '10.1.10.15']
    """
    return vim.vm.customization.GlobalIPSettings(dnsServerList=dnslist)


def sysprep_customization(hostname, domain='localhost.domain', workgroup='WORKGROUP', passwd='123456', sys_type='linux'):
    """
    hostname setting
    """
    sysprep_custom = None
    fixedname = vim.vm.customization.FixedName(name=hostname)
    if sys_type == 'linux':
        sysprep_custom = vim.vm.customization.LinuxPrep(hostName=fixedname,
                                                        domain=domain,
                                                        timeZone='Asia/Shanghai')
    elif sys_type == 'windows':
        # timeZone: https://technet.microsoft.com/en-us/library/ms145276(v=sql.90).aspx
        password_custom = vim.vm.customization.Password(value=passwd, plainText=True)
        guiunattended = vim.vm.customization.GuiUnattended(password=password_custom,
                                                           timeZone=210,
                                                           autoLogon=True,
                                                           autoLogonCount=1)
        userdata = vim.vm.customization.UserData(fullName=hostname,
                                                 orgName=hostname,
                                                 computerName=fixedname,
                                                 productId='')
        # identification = vim.vm.customization.Identification(joinDomain=domain,
        #                                                      domainAdmin=domain,
        #                                                      domainAdminPassword=password_custom)
        identification = vim.vm.customization.Identification(joinWorkgroup=workgroup)
        sysprep_custom = vim.vm.customization.Sysprep(guiUnattended=guiunattended,
                                                      userData=userdata,
                                                      identification=identification)
    return sysprep_custom


#def vm_add_disk(vm_moref, config_spec, vdev_node, ds_moref, disk_type, disk_size, disk_file_path=None):
#    """
#    """
#    (c_bus_number, d_unit_number) = vdev_node.split(':')
#    disk_spec = vim.vm.device.VirtualDeviceSpec()
#
#    # check or create disk controller dev
#    scsi_controllers = get_vm_scsi_controller_dev(vm_moref)
#    (controller, controller_spec) = _check_or_add_controller(scsi_controllers, int(c_bus_number),
#                                                             scsi_type='LsiLogicSAS',
#                                                             sharedbus_mode='physicalSharing')
#    # create disk dev
#    disk_spec.operation = "add"
#    disk_spec.device = vim.vm.device.VirtualDisk()
#    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
#    # https://github.com/vmware/pyvmomi/blob/master/docs/vim/vm/device/VirtualDiskOption/DiskMode.rst
#    disk_spec.device.backing.diskMode = 'persistent'
#    if disk_file_path:
#        disk_spec.device.backing.fileName = disk_file_path
#    else:
#        disk_spec.fileOperation = "create"
#    disk_spec.device.unitNumber = int(d_unit_number)
#    disk_spec.device.key = 2000 + int(c_bus_number) * 16 + int(d_unit_number)
#    disk_spec.device.controllerKey = controller.key
#    disk_spec.device.backing.datastore = ds_moref
#
#    # set disk type
#    _set_disk_type(disk_spec, disk_type)
#
#    # set disk size
#    disk_spec.device.capacityInKB = int(disk_size) * 1024 * 1024
#
#    if controller_spec:
#        config_spec.deviceChange.extend([controller_spec])
#    config_spec.deviceChange.extend([disk_spec])
#
#
#def vm_remove_disk(vm_moref, config_spec, disk_file_path):
#    """ remove disk device from vm
#    """
#    disk_devs = get_vm_disk_dev(vm_moref)
#    for dev in disk_devs:
#        if dev.backing.fileName == disk_file_path:
#            vm_remove_virtual_device(config_spec, dev, file_operation="destroy")
#            controller_unit_number = dev.controllerKey - 1000
#            vm_remove_scsi_controller(vm_moref, config_spec, controller_unit_number)
#            break


def create_attach_disks_config_spec(vm_moref, disks):
    """ create attach disks config spec
    """
    config_spec = vim.vm.ConfigSpec()
    scsi_controllers = get_vm_scsi_controller_dev(vm_moref)

    for disk in disks:
        (c_bus_number, d_unit_number) = disk['vdev_node'].split(':')
        # check or create disk controller dev
        (controller, controller_spec) = _check_or_add_controller(scsi_controllers, int(c_bus_number),
                                                                 scsi_type='LsiLogicSAS',
                                                                 sharedbus_mode='physicalSharing')
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = "add"
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.unitNumber = int(d_unit_number)
        disk_spec.device.key = 2000 + int(c_bus_number) * 16 + int(d_unit_number)
        disk_spec.device.controllerKey = controller.key

        # create disk backing info
        if disk.get('is_raw'):
            # create raw disk backing info
            disk_spec.device.backing = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
            disk_spec.device.backing.lunUuid = disk['lun_uuid']
            disk_spec.device.backing.deviceName = disk['device_name']
            # compatibilityMode: [physicalMode,virtualMode]
            disk_spec.device.backing.compatibilityMode = 'physicalMode'
        else:
            # create vmdk disk backing info
            disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            # set disk type
            _set_disk_type(disk_spec, disk['disk_type'])
            # set disk size
            disk_spec.device.capacityInKB = int(disk['disk_size']) * 1024 * 1024

        # https://github.com/vmware/pyvmomi/blob/master/docs/vim/vm/device/VirtualDiskOption/DiskMode.rst
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.backing.datastore = disk['ds_moref']

        if disk.get('file_path'):
            disk_spec.device.backing.fileName = disk['file_path']
        else:
            disk_spec.fileOperation = "create"

        if controller_spec:
            config_spec.deviceChange.extend([controller_spec])
            scsi_controllers.append(controller_spec.device)
        config_spec.deviceChange.extend([disk_spec])
    return config_spec


def create_remove_disks_config_spec(vm_moref, disks):
    """ create remove disks config spec
    """
    config_spec = vim.vm.ConfigSpec()
    disk_devs = get_vm_disk_dev(vm_moref)
    scsi_controller_devs = get_vm_scsi_controller_dev(vm_moref)
    controller_dev_dict = {}

    for disk in disks:
        disk_file_path = disk['file_path']
        for dev in disk_devs:
            if dev.backing.fileName == disk_file_path:
                vm_remove_virtual_device(config_spec, dev, file_operation="destroy")
                c_unit_number = dev.controllerKey - 1000
                # 记录从此控制器上移除的磁盘设备数
                if controller_dev_dict.get(c_unit_number):
                    controller_dev_dict[c_unit_number] += 1
                else:
                    controller_dev_dict[c_unit_number] = 1
                # 当此控制器上现有的磁盘设备数等于移除的磁盘设备数时，移除此scsi控制器
                for dev in scsi_controller_devs:
                    if dev.busNumber == c_unit_number:
                        if len(dev.device) == controller_dev_dict.get(c_unit_number):
                            vm_remove_virtual_device(config_spec, dev)
                        break
                break
            else:
                pass
        # end for
    # end for
    return config_spec


def vm_remove_scsi_controller(vm_moref, config_spec, bus_number):
    """ remove scsi controller device from vm
    """
    scsi_controller_devs = get_vm_scsi_controller_dev(vm_moref)
    for dev in scsi_controller_devs:
        if dev.busNumber == bus_number:
            if len(dev.device) == 1:
                vm_remove_virtual_device(config_spec, dev)
            break

def vm_remove_virtual_device(config_spec, dev, file_operation=None):
    """ remove virtual device from vm
    """
    device_spec = vim.vm.device.VirtualDeviceSpec()
    device_spec.operation = "remove"
    if file_operation:
        device_spec.fileOperation = file_operation
    device_spec.device = dev
    config_spec.deviceChange.extend([device_spec])


def _config_vm_disk(scsi_controllers, devs, disks):
    """
    @ parameters:
    @@ devs: list
    @@@ value: vim.vm.device.VirtualDisk moref
    @@ diskts: list
    @@ type: list
    @@@ value: dict
    @@@ value element:
    @@@@ disk_size: int
    @@@@ disk_type: [None|thin|eagerZeroedThick|preallocated]
    """
    while len(devs) > len(disks):
        disks.append(None)
    while len(devs) < len(disks):
        devs.append(None)
    controller_spec_list = []
    disk_spec_list = []
    allocated_vdev_node = []
    for (dev, disk) in zip(devs, disks):
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec_list.append(disk_spec)
        if disk is None:
            # remove
            disk_spec.operation = "remove"
            disk_spec.device = dev
        else:
            disk_size = disk['disk_size']
            disk_type = disk['disk_type']
            scsi_type = disk.get('scsi_type')
            if dev is None:
                # add
                disk_spec.fileOperation = "create"
                disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                disk_spec.device = vim.vm.device.VirtualDisk()
                disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                disk_spec.device.backing.diskMode = 'persistent'
                disk_spec.device.backing.fileName = "[%s]" % disk.get('ds_moref').name if disk.get('ds_moref') else None
                available_vdev_node = _get_available_vdev_node(devs, allocated_vdev_node)
                allocated_vdev_node.append(available_vdev_node)
                (c_bus_number, d_unit_number) = available_vdev_node.split(':')
                disk_spec.device.unitNumber = int(d_unit_number)
                disk_spec.device.key = 2000 + int(c_bus_number) * 16 + int(d_unit_number)
                (controller, controller_spec) = _get_edit_add_controller(scsi_controllers, int(c_bus_number), scsi_type)
                controller.device.append(disk_spec.device.key)
                disk_spec.device.controllerKey = controller.key
                controller_spec_list += [controller_spec] if controller_spec else []
            else:
                # edit
                disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                disk_spec.device = dev
            disk_spec.device.backing.datastore = disk.get('ds_moref')
            # update disk type
            _set_disk_type(disk_spec, disk_type)
            # update disk size
            new_disk_kb = int(disk_size) * 1024 * 1024
            if disk_spec.device.capacityInKB < new_disk_kb:
                disk_spec.device.capacityInKB = new_disk_kb
    return (disk_spec_list, controller_spec_list)


def _set_disk_type(disk_spec, disk_type):
    if disk_type is None:
        LOG.info('Same as the source disk format.')
    elif disk_type == constants.DISK_TYPE_THIN:
        disk_spec.device.backing.eagerlyScrub = None
        disk_spec.device.backing.thinProvisioned = True
    elif disk_type == constants.DISK_TYPE_PREALLOCATED:
        disk_spec.device.backing.eagerlyScrub = None
        disk_spec.device.backing.thinProvisioned = False
    elif disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
        disk_spec.device.backing.eagerlyScrub = True
        disk_spec.device.backing.thinProvisioned = False
    else:
        LOG.warning('Specifies the wrong disk format, so use the source disk format: disk_type=%s' % disk_type)


def _get_available_vdev_node(devs, allocated_vdev_node):
    all_vdev_node = ["%d:%d" % (a, b) for a in range(4) for b in range(16) if b != 7]
    used_vdev_node = ["%d:%d" % (dev.controllerKey-1000, dev.unitNumber) for dev in devs if dev]
    available_vdev_node = [n for n in all_vdev_node if n not in used_vdev_node and n not in allocated_vdev_node]
    if len(available_vdev_node) < 1:
        raise "No SCSI controllers are available !"
    return available_vdev_node[0]


def _get_edit_add_controller(scsi_controllers, bus_number, scsi_type=None):
    f_controller = None
    scsi_controller = None
    controller_spec = vim.vm.device.VirtualDeviceSpec()
    for c in scsi_controllers:
        if c.busNumber == bus_number:
            f_controller = c
    if f_controller:
        LOG.warning('Currently, SCSI controller type editing function is not provided.')
        scsi_controller = f_controller
        controller_spec = None
        # if scsi_type:
        #     new_scsi_type = constants.SCSI_CONTROLLER_TYPES.get(scsi_type)
        #     if new_scsi_type:
        #         controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        #         controller_spec.device = new_scsi_type()
        #         controller_spec.device.key = f_controller.key
        #         controller_spec.device.controllerKey = f_controller.controllerKey
        #         controller_spec.device.unitNumber = f_controller.unitNumber
        #         controller_spec.device.busNumber = f_controller.busNumber
        #         controller_spec.device.hotAddRemove = f_controller.hotAddRemove
        #         controller_spec.device.sharedBus = f_controller.sharedBus
        #         controller_spec.device.scsiCtlrUnitNumber = f_controller.scsiCtlrUnitNumber
        #         controller_spec.device.slotInfo = f_controller.slotInfo
        #         scsi_controller = controller_spec.device
    else:
        LOG.info('Add SCSI controller.')
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        default_scsi_type = constants.SCSI_CONTROLLER_TYPES['LsiLogicSAS']
        new_scsi_type = constants.SCSI_CONTROLLER_TYPES.get(scsi_type, default_scsi_type)
        controller_spec.device = new_scsi_type()
        controller_spec.device.key = 1000 + bus_number
        controller_spec.device.controllerKey = 100
        controller_spec.device.unitNumber = 3 + bus_number
        controller_spec.device.busNumber = bus_number
        controller_spec.device.hotAddRemove = True
        controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing('noSharing')
        controller_spec.device.scsiCtlrUnitNumber = 7
        # controller_spec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
        scsi_controller = controller_spec.device
    return (scsi_controller, controller_spec)


def _check_or_add_controller(scsi_controllers, bus_number,
                             scsi_type='LsiLogicSAS',
                             sharedbus_mode='noSharing'):
    """ check scsi controller device, or add controller device
    scsi_type: BusLogic, LsiLogic, LsiLogicSAS, ParaVirtual
    sharedBus: noSharing, virtualSharing, physicalSharing
    """
    f_controller = None
    scsi_controller = None
    controller_spec = None
    for c in scsi_controllers:
        if c.busNumber == bus_number:
            f_controller = c
    scsi_type = constants.SCSI_CONTROLLER_TYPES.get(scsi_type)
    if not f_controller:
        LOG.info('Add SCSI controller.')
        if not scsi_type:
            raise "scsi controller type error!"
        controller_spec = vim.vm.device.VirtualDeviceSpec()
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller_spec.device = scsi_type()
        controller_spec.device.key = 1000 + bus_number
        controller_spec.device.controllerKey = 100
        controller_spec.device.unitNumber = 3 + bus_number
        controller_spec.device.busNumber = bus_number
        controller_spec.device.hotAddRemove = True
        controller_spec.device.sharedBus = sharedbus_mode
        controller_spec.device.scsiCtlrUnitNumber = 7
        scsi_controller = controller_spec.device
    else:
        scsi_controller = f_controller
        if not isinstance(f_controller, scsi_type):
            LOG.warning('The current SCSI controller type does not match !')
        if sharedbus_mode!= f_controller.sharedBus:
            LOG.warning('The current SCSI controller bus share mode does not match !')
    return (scsi_controller, controller_spec)



def _config_vm_nic(devs, nets):
    """
    @ parameters:
    @@ devs:  list
    @@@ value: vim.vm.device.VirtualEthernetCard moref
    @@ nets: list
    @@@ value:
       [{'ip': '10.0.0.13', 'netmask': '255.255.255.0', 'gateway': '10.0.0.1',
         'pg_moid': 'dvportgroup-391', 'adapter_type': 'E1000'},]
    """
    while len(devs) > len(nets):
        nets.append(None)
    while len(devs) < len(nets):
        devs.append(None)
    nic_spec_list = []
    for (dev, net) in zip(devs, nets):
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec_list.append(nic_spec)
        if net is None:
            # remove
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
            nic_spec.device = dev
        else:
            pg_moid = net['pg_moid']
            pg_moref = net['pg_moref']
            adapter_type = net.get('adapter_type')
            is_backing_dvsp = False
            is_pg_dvsp = isinstance(pg_moref, vim.dvs.DistributedVirtualPortgroup)
            if dev is None:
                # add
                nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                default_adapter_type = constants.NIC_ADAPTER_TYPES.get('VMXNET3')
                new_adapter_type = constants.NIC_ADAPTER_TYPES.get(adapter_type, default_adapter_type)
                nic_spec.device = new_adapter_type()
                if is_pg_dvsp:
                    # add dvsp
                    nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                    nic_spec.device.backing.port = vim.dvs.PortConnection()
                    nic_spec.device.backing.port.portgroupKey = pg_moref.key
                    nic_spec.device.backing.port.switchUuid = pg_moref.config.distributedVirtualSwitch.uuid
                else:
                    # add svsp
                    nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                    nic_spec.device.backing.network = pg_moref
                    nic_spec.device.backing.deviceName = pg_moref.name
            else:
                is_backing_dvsp = isinstance(dev.backing, vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo)
                nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nic_spec.device = dev
                if is_backing_dvsp:
                    if dev.backing.port.portgroupKey == pg_moid:
                        # not operating
                        # continue
                        LOG.info('There is no need to modify the portgroup.')
                    elif is_pg_dvsp:
                        # edit dvsp
                        nic_spec.device.backing.port.portgroupKey = pg_moref.key
                        nic_spec.device.backing.port.switchUuid = pg_moref.config.distributedVirtualSwitch.uuid
                    else:
                        # edit svsp
                        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                        nic_spec.device.backing.network = pg_moref
                        nic_spec.device.backing.deviceName = pg_moref.name
                else:
                    if dev.backing.network._moId == pg_moid:
                        # not operating
                        # continue
                        LOG.info('There is no need to modify the portgroup.')
                    elif not is_pg_dvsp:
                        # edit svsp
                        nic_spec.device.backing.network = pg_moref
                        nic_spec.device.backing.deviceName = pg_moref.name
                    else:
                        # edit dvsp
                        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                        nic_spec.device.backing.port = vim.dvs.PortConnection()
                        nic_spec.device.backing.port.portgroupKey = pg_moref.key
                        nic_spec.device.backing.port.switchUuid = pg_moref.config.distributedVirtualSwitch.uuid
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.allowGuestControl = True
        nic_spec.device.connectable.connected = True
        # nic_spec.device.connectable.status = 'untried'
        nic_spec.device.wakeOnLanEnabled = True
        # nic_spec.device.addressType = 'assigned'
    return nic_spec_list


def get_vm_scsi_controller_dev(vm_moref):
    return [dev for dev in vm_moref.config.hardware.device \
            if isinstance(dev, vim.vm.device.VirtualSCSIController)]


def get_vm_disk_dev(vm_moref):
    return [dev for dev in vm_moref.config.hardware.device \
            if isinstance(dev, vim.vm.device.VirtualDisk)]


def get_vm_nic_adapter_dev(vm_moref):
    return [dev for dev in vm_moref.config.hardware.device \
            if isinstance(dev, vim.vm.device.VirtualEthernetCard)]


def create_configspec(num_cpu=1, num_core=1, memoryMB=512):
    """
    vim.vm.ConfigSpec(numCPUs=1, memoryMB=mem)
    vim.vm.device.VirtualDiskSpec()
    """
    # update cpu and memory config
    config_spec = vim.vm.ConfigSpec()
    # config_spec.memoryHotAddEnabled = True
    # config_spec.cpuHotAddEnabled = True
    # config_spec.cpuHotRemoveEnabled = True
    config_spec.numCPUs = num_cpu
    config_spec.numCoresPerSocket = num_core
    config_spec.memoryMB = memoryMB
    config_spec.uuid = str(uuid.uuid1())
    return config_spec


def create_relospec(esxi_moref, res_pool_moref, datastore_moref, disk_spec_list):
    """
    Create relocate spec.
    Disk Transform Rule:
        [thin, preallocated, eagerZeroedThick] -> thin
        [thin, preallocated]                   -> preallocated
        [thin, preallocated, eagerZeroedThick] -> eagerZeroedThick
    """
    # https://github.com/vmware/pyvmomi/blob/master/docs/vim/vm/RelocateSpec.rst
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore_moref
    relospec.pool = res_pool_moref
    relospec.host = esxi_moref

    # if disk_type == constants.DISK_TYPE_THIN or disk_type == constants.DISK_TYPE_PREALLOCATED:
    #     # relospec.transform = 'sparse'
    #     relospec.transform = vim.vm.RelocateSpec.Transformation('sparse')
    # elif disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
    #     # relospec.transform = 'flat'
    #     relospec.transform = vim.vm.RelocateSpec.Transformation('flat')

    for disk_spec in disk_spec_list:
        if disk_spec.operation != 'edit':
            continue
        disk_locator = vim.vm.RelocateSpec.DiskLocator()
        disk_locator.diskId = disk_spec.device.key
        disk_locator.diskBackingInfo = disk_spec.device.backing
        if disk_spec.device.backing.datastore:
            disk_locator.datastore = disk_spec.device.backing.datastore
        relospec.disk.append(disk_locator)
    return relospec


def create_clonespec(relospec, customspec, config_spec, poweron, is_template):
    """
    Create clone spec
    """
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.customization = customspec
    clonespec.config = config_spec
    clonespec.powerOn = poweron
    clonespec.template = is_template

    return clonespec


class VmCloneSpec():
    """
    make clone spec
    """
    def __init__(self, template_moref, sys_type, vm_uuid, vm_net, vm_disk, num_cpu, num_core, memoryMB, res_pool_moref, esxi_moref, datastore_moref, poweron, hostname, domain=None, dnslist=None, is_template=False):
        """ init clone spec
        """
        self.clone_spec = vim.vm.CloneSpec()
        self.clone_spec.powerOn = poweron
        self.clone_spec.template = is_template
        self.clone_spec.config = self.make_config_spec(template_moref,
                                                       vm_uuid,
                                                       vm_net,
                                                       vm_disk,
                                                       num_cpu,
                                                       num_core,
                                                       memoryMB)
        self.clone_spec.location = self.make_relocate_spec(res_pool_moref,
                                                           esxi_moref,
                                                           datastore_moref)
        self.clone_spec.customization = self.make_custom_spec(sys_type, vm_net, hostname,
                                                              domain, dnslist)

    def make_config_spec(self, template_moref, vm_uuid, vm_net, vm_disk, num_cpu=1, num_core=1, memoryMB=512):
        """
        vim.vm.ConfigSpec(numCPUs=1, memoryMB=mem)
        vim.vm.device.VirtualDiskSpec()
        """
        config_spec = vim.vm.ConfigSpec()
        # config_spec.memoryHotAddEnabled = True
        # config_spec.cpuHotAddEnabled = True
        # config_spec.cpuHotRemoveEnabled = True
        config_spec.numCPUs = num_cpu
        config_spec.numCoresPerSocket = num_core
        config_spec.memoryMB = memoryMB
        config_spec.uuid = vm_uuid

        # update device config
        dev_changes = []
        dev_nics = get_vm_nic_adapter_dev(template_moref)
        dev_disks = get_vm_disk_dev(template_moref)
        scsi_controllers = get_vm_scsi_controller_dev(template_moref)

        nic_spec_list = _config_vm_nic(dev_nics, vm_net)
        dev_changes += nic_spec_list
        (disk_spec_list, controller_spec_list) = _config_vm_disk(scsi_controllers, dev_disks, vm_disk)
        dev_changes += disk_spec_list
        dev_changes += controller_spec_list
        config_spec.deviceChange.extend(dev_changes)
        return config_spec

    def make_relocate_spec(self, res_pool_moref, esxi_moref, datastore_moref):
        """
        Create relocate spec.
        Disk Transform Rule:
            [thin, preallocated, eagerZeroedThick] -> thin
            [thin, preallocated]                   -> preallocated
            [thin, preallocated, eagerZeroedThick] -> eagerZeroedThick
        """
        # https://github.com/vmware/pyvmomi/blob/master/docs/vim/vm/RelocateSpec.rst
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.pool = res_pool_moref
        relocate_spec.host = esxi_moref
        relocate_spec.datastore = datastore_moref

        # if disk_type == constants.DISK_TYPE_THIN or disk_type == constants.DISK_TYPE_PREALLOCATED:
        #     # relospec.transform = 'sparse'
        #     relospec.transform = vim.vm.RelocateSpec.Transformation('sparse')
        # elif disk_type == constants.DISK_TYPE_EAGER_ZEROED_THICK:
        #     # relospec.transform = 'flat'
        #     relospec.transform = vim.vm.RelocateSpec.Transformation('flat')

        for disk_spec in self.clone_spec.config.deviceChange:
            if not isinstance(disk_spec.device, vim.vm.device.VirtualDeviceSpec) \
                    or disk_spec.operation != 'edit':
                continue
            disk_locator = vim.vm.RelocateSpec.DiskLocator()
            disk_locator.diskId = disk_spec.device.key
            disk_locator.diskBackingInfo = disk_spec.device.backing
            if disk_spec.device.backing.datastore:
                disk_locator.datastore = disk_spec.device.backing.datastore
            relocate_spec.disk.append(disk_locator)
        return relocate_spec

    def make_custom_spec(self, sys_type, vm_net, hostname, domain, dnslist):
        """
        Creating vm custom spec
        """
        custom_spec = vim.vm.customization.Specification()

        # Make sysprep (hostname/domain/timezone/workgroup) customization
        sysprep_custom = sysprep_customization(hostname=hostname, domain=domain, sys_type=sys_type)
        custom_spec.identity = sysprep_custom

        # Make network customization
        adaptermap_custom = network_customization(vm_net)
        custom_spec.nicSettingMap = adaptermap_custom

        # Make dns customization
        dns_custom = dns_customization(dnslist)
        custom_spec.globalIPSettings = dns_custom

        return custom_spec

