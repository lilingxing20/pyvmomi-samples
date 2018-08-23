# -*- coding:utf-8 -*-

"""
@@ function:
"""
from __future__ import absolute_import
import time
from pyVmomi import vim

from . import constants


def get_objs(content, vimfolder, vimtype):
    """
    Return an object by name, if name is None the first found object
    is returned
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ vimfolder: vim.Folder
    @@ vimtype: vim.ClusterComputeResource
    *           vim.Datacenter
    *           vim.Datastore
    *           vim.dvs.DistributedVirtualPortgroup
    *           vim.dvs.VmwareDistributedVirtualSwitch
    *           vim.Folder
    *           vim.HostSystem
    *           vim.Network
    *           vim.ResourcePool
    *           vim.StoragePod
    *           vim.VirtualApp
    *           vim.VirtualMachine

    """
    container = content.viewManager.CreateContainerView(vimfolder, vimtype, True)
    objs = container.view
    container.Destroy()
    return objs


def get_obj(content, vimtype, name, moid):
    """
    Return an object by uuid or name, if name and uuid is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ vimtype: vim.ClusterComputeResource
    *           vim.Datacenter
    *           vim.Datastore
    *           vim.dvs.DistributedVirtualPortgroup
    *           vim.dvs.VmwareDistributedVirtualSwitch
    *           vim.Folder
    *           vim.HostSystem
    *           vim.Network
    *           vim.ResourcePool
    *           vim.StoragePod
    *           vim.VirtualApp
    *           vim.VirtualMachine
    @@ name: obj name (str)

    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype,
                                                        True)
    if moid:
        for o in container.view:
            if o._moId == moid:
                obj = o
                break
        if not obj:
            raise Exception("%s not found by moid: %s" % (str(vimtype), moid))
    elif name:
        for o in container.view:
            if o.name == name:
                obj = o
                break
        if not obj:
            raise Exception("%s not found by name: %s" % (str(vimtype), moid))
    container.Destroy()
    return obj


def wait_for_task(task):
    """
    wait for a vCenter task to finish.
    """
    try:
        while True:
            if task.info.state == 'success':
                return (0, task.info.result)
            elif task.info.state == 'error':
                return (1, task.info.result)
            time.sleep(1)
    except Exception as ex:
        return (-1, "无法获取任务结果")


def get_contains_obj(folder_obj):
    obj_list = []
    for obj in folder_obj.childEntity:
        if isinstance(obj, vim.Folder):
            obj_list += get_contains_obj(obj)
        else:
            obj_list.append(obj)
    return obj_list


def retrieve_objects(content, folder):
    """
    Recursive search object in the directory
    """
    obj_list = []
    folder_mor = content.searchIndex.FindByInventoryPath(folder)
    if folder_mor:
        for obj in folder_mor.childEntity:
            if isinstance(obj, vim.Folder):
                child_folder = "%s/%s" % (folder, obj.name)
                obj_list += retrieve_objects(content, child_folder)
            obj_list.append(obj)
    return obj_list


def retrieve_folder_tree(folder_obj, base_dir=None):
    obj_list = []
    for obj in folder_obj.childEntity:
        new_dir = base_dir + '/' + obj.name if base_dir else obj.name
        if isinstance(obj, vim.Folder):
            obj_list += retrieve_folder_tree(obj, new_dir)
    if base_dir:
        obj_list.append({'name': base_dir, 'moid': folder_obj._moId})
    return obj_list


def get_datacenter_moref(content, name=None, moid=None):
    """
    Return a DC object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: vm name (str)
    """
    dc_moref = get_obj(content, [vim.Datacenter], name, moid)
    return dc_moref


def get_cluster_moref(content, name=None, moid=None):
    """
    Return a Cluster object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: datastore name (str)
    """
    cluster_moref = get_obj(content, [vim.ClusterComputeResource], name, moid)
    return cluster_moref


def get_host_moref(content, name=None, uuid=None, moid=None):
    """
    Return a Hostsystem object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: esxi host name (str)
    @@ uuid: esxi host uuid (str)

    """
    host_obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.HostSystem],
                                                        True)
    if moid is not None:
        for o in container.view:
            if o._moId == moid:
                host_obj = o
                break
        if not host_obj:
            raise Exception("Host not found by moid: %s" % moid)
    elif uuid is not None:
        for o in container.view:
            if o.hardware.systemInfo.uuid == uuid:
                host_obj = o
                break
        if not host_obj:
            raise Exception("Host not found by uuid: %s" % uuid)
    elif name is not None:
        for o in container.view:
            if o.name == name:
                host_obj = o
                break
        if not host_obj:
            raise Exception("Host not found by name: %s" % name)
    container.Destroy()
    return host_obj


def get_datastore_moref(content, name=None, uuid=None, moid=None):
    """
    Return a DataStore object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: datastore name (str)
    @@ uuid: datastore uuid (str)

    """
    ds_moref = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.Datastore],
                                                        True)
    if moid is not None:
        for o in container.view:
            if o._moId == moid:
                ds_moref = o
                break
        if not ds_moref:
            raise Exception("Datastore not found by moid: %s" % moid)
    elif uuid is not None:
        for o in container.view:
            if o.info.vmfs.uuid == uuid:
                ds_moref = o
                break
        if not ds_moref:
            raise Exception("Datastore not found by uuid: %s" % uuid)
    elif name is not None:
        for o in container.view:
            if o.name == name:
                ds_moref = o
                break
        if not ds_moref:
            raise Exception("Datastore not found by name: %s" % name)
    container.Destroy()
    return ds_moref


def get_vm_moref(content, name=None, uuid=None, moid=None):
    """
    Return a VM object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: vm name (str)
    @@ uuid: vm uuid (str)

    """
    vm_obj = None
    if uuid is not None:
        vm_obj = find_vm_by_uuid(content, None, uuid)
        if not vm_obj:
            raise Exception("Vm not found by uuid: %s" % uuid)
    else:
        container = content.viewManager.CreateContainerView(content.rootFolder,
                                                            [vim.VirtualMachine],
                                                            True)
        if moid is not None:
            for o in container.view:
                if o._moId == moid:
                    vm_obj = o
                    break
            if not vm_obj:
                raise Exception("Vm not found by moid: %s" % moid)
        elif name is not None:
            for o in container.view:
                if o.name == name:
                    vm_obj = o
                    break
            if not vm_obj:
                raise Exception("Vm not found by name: %s" % name)
        container.Destroy()
    return vm_obj


def get_portgroup_moref(content, name=None, moid=None):
    """
    Return a portgroup object by name, if name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: portgroup name (str)
    """
    pg_moref = get_obj(content, [vim.Network], name, moid)
    return pg_moref


def filter_vapp_obj(content, name):
    """
    Return a vApp object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: vapp name (str)
    """
    vapp_obj = get_obj(content, [vim.VirtualApp], name, None)
    return vapp_obj


def get_res_pool_moref(content, name):
    """
    Return a Resource Pool object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: vm name (str)
    """
    rp_obj = get_obj(content, [vim.ResourcePool], name, None)
    return rp_obj


def filter_vmfolder_obj(content, name):
    """
    Return a vm folder object by uuid or name, if uud and name is None return None
    @ parameters:
    @@ content: vim.ServiceInstanceContent
    @@ name: vm name (str)
    """
    destfolder_obj = get_obj(content, [vim.Folder], name, None)
    return destfolder_obj


def get_folder_obj(folder_obj, folder_name_list):
    for obj in folder_obj.childEntity:
        if folder_name_list and obj.name == folder_name_list[0]:
            if len(folder_name_list) > 1 and isinstance(obj, vim.Folder):
                return get_folder_obj(obj, folder_name_list[1:])
            else:
                return obj
    return folder_obj


def get_system_type(config_spec):
    """
    @ parameters:
    @@ config_spece type: vim.vm.ConfigInfo
    """
    if config_spec.guestId in constants.WIN_OS_TYPES:
        sys_type = 'windows'
    elif config_spec.guestId in constants.LINUX_OS_TYPES:
        sys_type = 'linux'
    else:
        sys_type = 'linux'
    return sys_type


def get_os_type(guest_id):
    os_type = 'linux'
    if guest_id in constants.WIN_OS_TYPES:
        os_type = 'windows'
    elif guest_id in constants.LINUX_OS_TYPES:
        os_type = 'linux'
    return os_type


def find_vm_by_uuid(content, dc_name, uuid, is_instance_uuid=False):
    """
    """
    dc_mor = None
    if dc_name:
        dc_mor = get_datacenter_moref(content, name=dc_name)
    vm_mor = content.searchIndex.FindByUuid(dc_mor, uuid, True, is_instance_uuid)
    return vm_mor


def find_vm_by_ip(content, dc_name, ip):
    """
    """
    dc_mor = None
    if dc_name:
        dc_mor = get_datacenter_moref(content, name=dc_name)
    vm_mor = content.searchIndex.FindByIp(dc_mor, ip, True)
    return vm_mor


def find_host_by_ip(content, dc_name, ip):
    """
    """
    dc_mor = None
    if dc_name:
        dc_mor = get_datacenter_moref(content, name=dc_name)
    host_mor = content.searchIndex.FindByIp(dc_mor, ip, False)
    return host_mor


def extended_network_moref(content, vm_net):
    """
    Extended attributes: moref
    """
    for n in vm_net:
        pg_moref = get_portgroup_moref(content, moid=n.get('pg_moid'))
        if pg_moref:
            n['pg_moref'] = pg_moref
    return vm_net


def extended_datastore_moref(content, vm_disk):
    """
    Extended attributes: moref
    """
    for d in vm_disk:
        # ds_moref = utils.get_datastore_moref(content, name=d.get('ds_name'))
        ds_moref = get_datastore_moref(content, moid=d.get('ds_moid'))
        if ds_moref:
            d['ds_moref'] = ds_moref
    return vm_disk


def exchange_maskint(mask_int):
    bin_arr = ['0' for i in range(32)]
    for i in range(mask_int):
        bin_arr[i] = '1'
    tmpmask = [''.join(bin_arr[i * 8:i * 8 + 8]) for i in range(4)]
    tmpmask = [str(int(tmpstr, 2)) for tmpstr in tmpmask]
    return '.'.join(tmpmask)


def datastore_capacity_free(ds_obj):
    """
    To json information for a particular datastore
    @ ds_obj: vim.DataStore
    """
    ds_details = {}
    ds_details['name'] = ds_obj.name
    ds_details['capacity'] = ds_obj.summary.capacity
    ds_details['freeSpace'] = ds_obj.summary.freeSpace
    return ds_details
