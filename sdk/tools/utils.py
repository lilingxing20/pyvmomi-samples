# -*- coding:utf-8 -*-

"""
@@ function:
@ get_obj: get Return an object by name, if name is None the first found object
           is returned

"""

from pyVmomi import vim
import constants


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


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the first found object
    is returned
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
    for o in container.view:
        if name:
            if o.name == name:
                obj = o
                break
        else:
            obj = o
            break
    container.Destroy()
    return obj


def wait_for_task(task):
    """
    wait for a vCenter task to finish.
    """
    while True:
        if task.info.state == 'success':
            return (0, task.info.result)
        elif task.info.state == 'error':
            return (1, task.info.result)


def filter_datacenter_obj(content, datacenter_name):
    """
    @ parameters:
    @@ datacenter_name: if none get the first one
    """
    dc_obj = get_obj(content, [vim.Datacenter], datacenter_name)
    return dc_obj


def filter_vmfolder_obj(content, vmfolder_name):
    """
    @ parameters:
    @@ vmfolder_name: if none get the first one
    """
    destfolder_obj = None
    if vmfolder_name:
        destfolder_obj = get_obj(content, [vim.Folder], vmfolder_name)
    return destfolder_obj


def filter_vm_obj(content, vm_name):
    """
    @ parameters:
    @@ vm_name: if none get the first one
    """
    if vm_name:
        cluster_obj = get_obj(content, [vim.VirtualMachine], vm_name)
    else:
        cluster_obj = None
    return cluster_obj


def filter_datastore_obj(content, datastore_name):
    """
    @ parameters:
    @@ datastore_name: if none get the first one
    """
    ds_obj = get_obj(content, [vim.Datastore], datastore_name)
    return ds_obj


def filter_cluster_obj(content, cluster_name):
    """
    @ parameters:
    @@ cluster_name: if none get the first one
    """
    cluster_obj = get_obj(content, [vim.ClusterComputeResource], cluster_name)
    return cluster_obj


def get_network_obj(content, net_name):
    """
    @ parameters:
    @@ net_name: if none return none
    """
    nic_obj = None
    if net_name:
        nic_obj = get_obj(content, [vim.Network], net_name)
    return nic_obj


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
