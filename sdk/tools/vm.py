# -*- coding:utf-8 -*-

"""
@@ function:
@ vm_info_json: get VM details

"""


from pyVmomi import vim
import constants


def vm_info_json(vm_obj):
    """
    To json information for a particular virtual machine
    @ vm_obj: vim.VirtualMachine
    """
    vm_details = {}
    vm_details["name"] = vm_obj.summary.config.name
    vm_details["path"] = vm_obj.summary.config.vmPathName
    vm_details["guest"] = vm_obj.summary.config.guestFullName
    vm_details["instanceUuid"] = vm_obj.summary.config.instanceUuid
    vm_details["uuid"] = vm_obj.summary.config.uuid
    vm_details["numCpu"] = vm_obj.summary.config.numCpu
    vm_details["memorySizeMB"] = vm_obj.summary.config.memorySizeMB
    vm_details["esxiHost"] = vm_obj.summary.runtime.host.name
    vm_details["state"] = vm_obj.summary.runtime.powerState

    vm_details["toolsVersion"] = vm_obj.guest.toolsVersion
    vm_details["guestFullName"] = vm_obj.guest.guestFullName
    vm_details["guestId"] = vm_obj.guest.guestId
    vm_details["hostName"] = vm_obj.guest.hostName

    vm_details["numCoresPerSocket"] = vm_obj.config.hardware.numCoresPerSocket
    vm_details["numCPU"] = vm_obj.config.hardware.numCPU
    vm_details["memoryMB"] = vm_obj.config.hardware.memoryMB

    disks_info = disk_info_json(vm_obj.config.hardware.device)
    vm_details['disk'] = disks_info
    vm_details['is_template'] = vm_obj.config.template

    vm_details["ip"] = vm_obj.guest.ipAddress
    vm_ipv4 = []
    vm_ipv6 = []
    for net in vm_obj.guest.net:
        if net.ipAddress:
            vm_ipv4.append(net.ipAddress[0])
            if len(net.ipAddress) >= 2:
                vm_ipv6.append(net.ipAddress[1])
    vm_details["ipv4"] = vm_ipv4
    vm_details["ipv6"] = vm_ipv6
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
                disk_type = constants.DISK_TYPE_THIN
            elif device_obj.backing.eagerlyScrub:
                disk_type = constants.DISK_TYPE_EAGER_ZEROED_THICK
            else:
                disk_type = constants.DISK_TYPE_PREALLOCATED
        disk_info['diskType'] = disk_type
        disk_info['isRawDisk'] = is_raw_disk

        disks_info.append(disk_info)
    return disks_info


def config_vm_network(vm_net):
    """
    VM network setting
    """
    adaptermaplist = []
    for net in vm_net:
        adaptermap = vim.vm.customization.AdapterMapping()
        fixedip = vim.vm.customization.FixedIp(ipAddress=net.get('ip'))
        adaptermap.adapter = vim.vm.customization.IPSettings(ip=fixedip,
                                                             subnetMask=net.get('netmask'),
                                                             gateway=net.get('gateway'))
        adaptermaplist.append(adaptermap)
    return adaptermaplist


def config_vm_dns(dnslist):
    """
    dnslist = ['10.1.10.14', '10.1.10.15']
    """
    return vim.vm.customization.GlobalIPSettings(dnsServerList=dnslist)


def config_vm_hostname(hostname, domain='localhost.domain'):
    """
    hostname setting
    """
    fixedname = vim.vm.customization.FixedName(name=hostname)
    return vim.vm.customization.LinuxPrep(domain=domain,
                                          hostName=fixedname)


def create_vm_customspec(adaptermap, globalip, identity):
    """
    Creating vm custom spec
    """
    customspec = vim.vm.customization.Specification(nicSettingMap=adaptermap,
                                                    globalIPSettings=globalip,
                                                    identity=identity)
    return customspec


def create_relospec(res_pool_obj, datastore_obj, disktype):
    """
    Create relocate spec
    """
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore_obj
    relospec.pool = res_pool_obj
    if disktype:
        if disktype == constants.DISK_TYPE_THIN:
            relospec.transform = 'sparse'
        elif disktype == constants.DISK_TYPE_PREALLOCATED \
                or disktype == constants.DISK_TYPE_EAGER_ZEROED_THICK:
            relospec.transform = 'flat'
    return relospec


def create_clonespec(relospec, customspec, vm_conf, poweron, is_template):
    """
    Create clone spec
    """
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.customization = customspec
    clonespec.config = vm_conf
    clonespec.powerOn = poweron
    clonespec.template = is_template

    return clonespec


def change_disk_type_size(device_obj, disktype, disksize):
    """
    @ parameters:
    @@ device_obj:
    @@@ type: vim.vm.device.VirtualDisk
    @@ disktype: [thin|eagerZeroedThick|preallocated]
    """
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    disk_spec.device = device_obj
    if disktype:
        if disktype == constants.DISK_TYPE_THIN:
            # disk_spec.device.backing.eagerlyScrub = None
            disk_spec.device.backing.thinProvisioned = True
        elif disktype == constants.DISK_TYPE_PREALLOCATED:
            # disk_spec.device.backing.eagerlyScrub = False
            disk_spec.device.backing.thinProvisioned = False
        elif disktype == constants.DISK_TYPE_EAGER_ZEROED_THICK:
            disk_spec.device.backing.eagerlyScrub = True
            # disk_spec.device.backing.thinProvisioned = False
#    else:
#        LOG.info('The same as the virtual machine template source format.')

    new_disk_kb = int(disksize) * 1024 * 1024
    disk_spec.device.capacityInKB = new_disk_kb
    return disk_spec


def update_vm_config(template_obj, disktype, disksize, cpunum=1, corenum=1, memoryMB=512):
    """
    vim.vm.ConfigSpec(numCPUs=1, memoryMB=mem)
    vim.vm.device.VirtualDiskSpec()
    """
    # update cpu and memory config
    vm_conf = vim.vm.ConfigSpec()
    vm_conf.numCPUs = cpunum
    vm_conf.numCoresPerSocket = corenum
    vm_conf.memoryMB = memoryMB

    # update disk device config
    disk_changes = []
    for dev in template_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            disk_spec = change_disk_type_size(dev, disktype, disksize)
            disk_changes.append(disk_spec)
    if not disk_changes:
        raise RuntimeError('Virtual disk could not be found.')

    vm_conf.deviceChange = disk_changes
    return vm_conf
