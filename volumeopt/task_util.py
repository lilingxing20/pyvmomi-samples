#!/usr/bin/env python
# -*- coding:utf-8 -*-



from i18n import _, _LE, _LW
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


def wait_for_task(task):
    """Wait for a vCenter task to finish.
    """
    while True:
        if task.info.state == 'success':
            return (True, task.info)
        elif task.info.state == 'error':
            return (False, task.info)


def create_inventory_folder(folder_ref, new_folder_name):
    try:
        vmfolder = folder_ref.CreateFolder(new_folder_name)
    except vim.fault.DuplicateName:
        LOG.error('Another object in the same folder has the target name.')
    except vim.fault.InvalidName:
        LOG.error(_LE('The new folder name (%s) is not a valid entity name.'), new_folder_name)
    return vmfolder


def create_vm_task(folder_ref, resource_pool, host_ref, create_spec):
    """For create vm methods."""
    LOG.debug("Creating vm with spec: %s.", create_spec)
    task = folder_ref.CreateVM_Task(config=create_spec,
                                    pool=resource_pool,
                                    host=host_ref)
    (task_state, task_info) = wait_for_task(task)
    vm_ref = task_info.result
    if task_state:
        LOG.info("Successfully created volume vm_ref: %s.", vm_ref)
    else:
        LOG.info("Created vm error !")
    return vm_ref

def destroy_vm_task(vm_ref):
    try:
        task = vm_ref.Destroy_Task()
        (status, info) = wait_for_task(task)
    except vmodl.MethodFault as error:
        LOG.exception("Caught vmodl fault : " + error.msg)
    return status, info

def reconfigure_vm(vm_ref, config_spec):
    """Reconfigure a VM according to the config spec."""
    reconfig_task =vm_ref.ReconfigVM_Task(spec=config_spec)
    return wait_for_task(reconfig_task)
