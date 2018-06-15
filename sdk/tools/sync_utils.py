# -*- coding:utf-8 -*-

from pyVmomi import vim
from past.utils import old_div
from urllib.request import unquote

from . import utils
from . import pchm
from . import constants


_DATACENTER = ['name',
               'hostFolder',
               'vmFolder']
_CLUSTER = ['name',
            'host',
            'datastore',
            'network']
_HOST = ['name',
         "config.storageDevice.scsiLun",
         'config.network.dnsConfig.hostName',
         'config.network.dnsConfig.domainName',
         'config.ipmi.bmcIpAddress',
         'config.product.fullName',
         'hardware.biosInfo.biosVersion',
         'hardware.cpuInfo.numCpuPackages',
         'hardware.cpuInfo.numCpuCores',
         'hardware.cpuInfo.numCpuThreads',
         'hardware.cpuInfo.hz',
         'hardware.systemInfo.vendor',
         'hardware.systemInfo.model',
         'runtime.connectionState',
         'runtime.powerState',
         'runtime.bootTime',
         'summary.managementServerIp',
         'summary.hardware.memorySize',             # host.memory
         'summary.hardware.uuid',                   # host.uuid
         'summary.hardware.numCpuThreads',          # host.cpu_count
         'summary.hardware.cpuMhz',                 # host.processor_speed
         'summary.hardware.cpuModel',               # host.cpu_model
         'summary.hardware.numCpuCores',            # host.core_count
         'summary.hardware.model',                  # host.model
         'summary.hardware.vendor',                 # host.vendor
         'summary.quickStats.overallMemoryUsage',
         'summary.quickStats.overallCpuUsage',
         'vm',
         'network',
         'datastore']
_NETWORK = ['name', 'summary.accessible', 'host', 'vm']
_DATASTORE = ['name',
              'overallStatus',
              'vmfs',
              # 'info.vmfs.ssd',
              # 'info.vmfs.local',
              # 'info.vmfs.uuid',
              'summary.capacity',
              'summary.freeSpace',
              'summary.url',
              'summary.accessible',
              'summary.multipleHostAccess',
              'summary.type']

_VM = ['name',
       'summary.config.vmPathName',
       'summary.config.guestFullName',
       'summary.config.instanceUuid',
       'summary.config.uuid',
       'summary.config.annotation',      # vm.description
       'summary.config.numCpu',          # vm.cpu_count
       'summary.config.memorySizeMB',    # vm.memory
       'summary.config.numEthernetCards',
       'summary.config.numVirtualDisks',
       'summary.runtime.host',           # esxi host
       'summary.runtime.powerState',     # vm.run_status
       'summary.storage.committed',      # diskGB / 1024**3
       'config.template',
       'config.hardware.device',
       'config.hardware.numCoresPerSocket',
       'config.hardware.numCPU',
       'config.hardware.memoryMB',
       'config.version',
       'guest.guestId',
       'guest.guestState',
       'guest.hostName',
       'guest.ipAddress',
       'guest.net',
       'guest.toolsRunningStatus',       # guestToolsExecutingScripts, guestToolsNotRunning, guestToolsRunning
       ]


# sync_flat:
#  0: dc
#     dc:tempalte
#     dc:vmfolder
#     dc:cluster:[host, datastore, portgroup]
#     dc:cluster:host:[vm]
#     dc:cluster:host:vm:[vmdisk, vmport]
#  1: dc:[tempalte, vmfolder]
#  2: dc:tempalte
#     dc:vmfolder
#     dc:cluster:[host, datastore, portgroup]
def get_vc_properties(si, sync_flat=0):
    dcs = get_dc_properties(si)
    clusters = get_cluster_properties(si, key='moid')
    dss = get_ds_properties(si, key='moid')
    pgs = get_pg_properties(si, key='moid')
    hosts = get_host_properties(si, key='moid')
    vms = get_vm_properties(si, key='moid')

    template_vms = []
    for vmk, vmv in vms.items():
        if vmv['config.template']:
            template_vms.append(vmv)
    for hk, hv in hosts.items():
        hv['vms'] = [vms[moid] for moid in hv['vm'] if moid in vms]
    for ck, cv in clusters.items():
        cv['hosts'] = [hosts[moid] for moid in cv['host'] if moid in hosts]
        cv['dss'] = [dss[moid] for moid in cv['datastore'] if moid in dss]
        cv['pgs'] = [pgs[moid] for moid in cv['network'] if moid in pgs]
    for dc in dcs:
        dc['hosts'] = []
        dc['clusters'] = []
        for c_moid in dc['hosts']:
            if c_moid.startswith('domain-'):
                dc['clusters'].append(clusters[c_moid])
            else:
                dc['hosts'].append(hosts[c_moid])
    return (dcs, template_vms)


def get_vc_all_properties(si):
    dcs = get_dc_properties(si)
    clusters = get_cluster_properties(si, key='moid')
    dss = get_ds_properties(si, key='moid')
    pgs = get_pg_properties(si, key='moid')
    hosts = get_host_properties(si, key='moid')
    vms = get_vm_properties(si, key='moid')

    for hk, hv in hosts.items():
        hv['vms'] = [vms[moid] for moid in hv['vm'] if moid in vms]
    for ck, cv in clusters.items():
        cv['hosts'] = [hosts[moid] for moid in cv['host'] if moid in hosts]
        cv['dss'] = [dss[moid] for moid in cv['datastore'] if moid in dss]
        cv['pgs'] = [pgs[moid] for moid in cv['network'] if moid in pgs]
    for dc in dcs:
        dc['clusters'] = [clusters[moid] for moid in dc['cluster'] if moid in clusters]
        # dc['hosts'] = [hosts[moid] for moid in dc['host'] if moid in hosts]
        # dc['templates'] = [vms[moid] for moid in dc['vm'] if moid in vms and vms[moid]['config.template']]
    templates = []
    for vmk, vmv in vms.items():
        if vmv['config.template']:
            templates.append(vmv)
    return (dcs, templates)


def get_vc_template_properties(si):
    vms = get_vm_properties(si, key='moid')
    template_vms = []
    for vmk, vmv in vms.items():
        if vmv['config.template']:
            template_vms.append(vmv)
    return template_vms


def get_vc_res_properties(si):
    dcs = get_dc_properties(si)
    clusters = get_cluster_properties(si, key='moid')
    dss = get_ds_properties(si, key='moid')
    pgs = get_pg_properties(si, key='moid')
    hosts = get_host_properties(si, key='moid')

    for ck, cv in clusters.items():
        cv['hosts'] = [hosts[moid] for moid in cv['host'] if moid in hosts]
        cv['dss'] = [dss[moid] for moid in cv['datastore'] if moid in dss]
        cv['pgs'] = [pgs[moid] for moid in cv['network'] if moid in pgs]
    for dc in dcs:
        dc['hosts'] = []
        dc['clusters'] = []
        for c_moid in dc['hosts']:
            if c_moid.startswith('domain-'):
                dc['clusters'].append(clusters[c_moid])
            else:
                dc['hosts'].append(hosts[c_moid])
    return dcs


def get_dc_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.Datacenter], container)
    dc_refs = pchm.collect_properties(si, view_ref, vim.Datacenter, _DATACENTER)
    pchm.destroy_container_view(view_ref)
    dc_properties = parse_dc_properties(dc_refs, key)
    return dc_properties


def get_cluster_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.ClusterComputeResource], container)
    cluster_refs = pchm.collect_properties(si, view_ref, vim.ClusterComputeResource, _CLUSTER)
    pchm.destroy_container_view(view_ref)
    cluster_properties = parse_cluster_properties(cluster_refs, key)
    return cluster_properties


def get_ds_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.Datastore], container)
    ds_refs = pchm.collect_properties(si, view_ref, vim.Datastore, _DATASTORE)
    pchm.destroy_container_view(view_ref)
    ds_properties = parse_ds_properties(ds_refs, key)
    return ds_properties


def get_pg_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.Network], container)
    pg_refs = pchm.collect_properties(si, view_ref, vim.Network, _NETWORK)
    pchm.destroy_container_view(view_ref)
    pg_properties = parse_pg_properties(pg_refs, key)
    return pg_properties


def get_host_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.HostSystem], container)
    host_refs = pchm.collect_properties(si, view_ref, vim.HostSystem, _HOST)
    pchm.destroy_container_view(view_ref)
    host_properties = parse_host_properties(host_refs, key)
    return host_properties


def get_vm_properties(si, container=None, include_mors=False, key=None):
    view_ref = pchm.get_container_view(si, [vim.VirtualMachine], container)
    vm_refs = pchm.collect_properties(si, view_ref, vim.VirtualMachine, _VM)
    pchm.destroy_container_view(view_ref)
    vm_properties = parse_vm_properties(vm_refs, key)
    return vm_properties


# Parse DataCenter properties
def parse_dc_properties(dc_refs, key=None):
    dcs = pchm.parse_properties(dc_refs)
    for dc in dcs:
        dc['vmfolder'] = retrieve_folder_tree(dc['vmFolder'])
        frv_objs = retrieve_obj_by_folder(dc['vmFolder'])
        dc['vm'] = [o._moId for o in frv_objs if o._moId.startswith('vm-')]
        fhc_objs = retrieve_obj_by_folder(dc['hostFolder'])
        dc['host'] = [o._moId for o in fhc_objs if o._moId.startswith('host-')]
        dc['cluster'] = [o._moId for o in fhc_objs if o._moId.startswith('domain-')]
    return dict([(o[key], o) for o in dcs if key in o]) if key else dcs


# Parse Cluster properties
def parse_cluster_properties(cluster_refs, key=None):
    clusters = pchm.parse_properties(cluster_refs)
    for c in clusters:
        for k in c:
            if isinstance(c[k], list):
                c[k] = [o._moId for o in c[k]]
    return dict([(o[key], o) for o in clusters if key in o]) if key else clusters


# Parse Host properties
def parse_host_properties(host_refs, key=None):
    hosts = pchm.parse_properties(host_refs)
    for h in hosts:
        for k in h:
            if isinstance(h[k], list):
                if (h[k].__class__.__name__ == 'ManagedObject[]'):
                    h[k] = [o._moId for o in h[k]]
                elif (h[k].__class__.__name__ == 'vim.host.ScsiLun[]'):
                    scsiluns=[]
                    for sl in h[k]:
                        if sl.__class__.__name__ == 'vim.host.ScsiDisk':
                            scsilun = {
                                       # vim.host.ScsiLun
                                       'deviceName': sl.deviceName,
                                       'deviceType': sl.deviceType,
                                       'key': sl.key,
                                       'uuid': sl.uuid,
                                       'canonicalName': sl.canonicalName,
                                       'displayName': sl.displayName,
                                       'lunType': sl.lunType,
                                       'vendor': sl.vendor,
                                       'model': sl.model,
                                       'revision': sl.revision,
                                       'scsiLevel': sl.scsiLevel,
                                       'operationalState': ','.join(sl.operationalState),
                                       'vStorageSupport': sl.vStorageSupport,
                                       'protocolEndpoint': sl.protocolEndpoint,
                                       # vim.host.ScsiDisk
                                       'blockSize': sl.capacity.blockSize,
                                       'block': sl.capacity.block,
                                       'devicePath': sl.devicePath,
                                       'localDisk': sl.localDisk,
                                       'ssd': sl.ssd,
                                       }
                            scsiluns.append(scsilun)
                        else:
                            pass
                    h[k] = scsiluns
    return dict([(o[key], o) for o in hosts if key in o]) if key else hosts


# Parse Portgroup properties
def parse_pg_properties(pg_refs, key=None):
    pgs = pchm.parse_properties(pg_refs)
    for pg in pgs:
        for k in pg:
            if isinstance(pg[k], list):
                pg[k] = [o._moId for o in pg[k]]
    return dict([(o[key], o) for o in pgs if key in o]) if key else pgs


# Parse DataStore properties
def parse_ds_properties(ds_refs, key=None):
    return pchm.parse_properties(ds_refs, key=key)


# Parse VM properties
def parse_vm_properties(vm_refs, key=None):
    vms = pchm.parse_properties(vm_refs)
    for vm in vms:
        (vm_disks, vm_nics) = get_vm_device_info(vm.pop('config.hardware.device'))
        vm['disk'] = vm_disks
        vm_nets = get_vm_nic_info(vm_nics, vm.pop('guest.net'))
        vm['network'] = vm_nets
        vm['summary.runtime.host'] = vm['summary.runtime.host'].name
        vm['os_type'] = utils.get_os_type(vm.get('guest.guestId'))
    return dict([(o[key], o) for o in vms if key in o]) if key else vms


def get_vm_nic_info(net_adapters, vm_net_mo):
    """
    """
    for adapter in net_adapters:
        key = adapter['key']
        for net in vm_net_mo:
            if key != net.deviceConfigId:
                continue
            if net.network:
                adapter['portgroup'] = unquote(net.network)
            adapter['connected'] = net.connected
            if not net.ipConfig:
                break
            _ip_list = []
            for ipconfig in net.ipConfig.ipAddress:
                # if ipconfig.ipAddress.startswith('fe80'):
                if len(ipconfig.ipAddress) > 15:  # len(xxx.xxx.xxx.xxx) == 15
                    continue
                _ip_list.append(ipconfig.ipAddress)
                _ip_list.append({'ip': ipconfig.ipAddress,
                                 'prefix': ipconfig.prefixLength,
                                 'netmask': utils.exchange_maskint(int(ipconfig.prefixLength))})
            adapter['ipv4'] = ','.join(_ip_list)
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
    net_info['netmask'] = ''
    return net_info


def retrieve_folder_tree(folder_obj, base_dir=None):
    obj_list = []
    for obj in folder_obj.childEntity:
        new_dir = base_dir + '/' + obj.name if base_dir else obj.name
        if isinstance(obj, vim.Folder):
            obj_list += retrieve_folder_tree(obj, new_dir)
    if base_dir:
        obj_list.append({'name': base_dir, 'moid': folder_obj._moId})
    return obj_list


def retrieve_obj_by_folder(folder_obj):
    obj_list = []
    for obj in folder_obj.childEntity:
        if isinstance(obj, vim.Folder):
            obj_list += retrieve_obj_by_folder(obj)
        obj_list.append(obj)
    return obj_list
