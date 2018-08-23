# -*- coding:utf-8 -*-

from __future__ import absolute_import

import logging
import uuid

from pyVmomi import vim, vmodl

from .session import VcenterSession
from .tools import vm, vmops, utils, task_utils


LOG = logging.getLogger(__name__)
# python3 default encoding: utf-8
# reload(sys)
# sys.setdefaultencoding('utf-8')


class VMwareClient(object):
    """ vmware client
    """

    def __init__(self, vcenter_info):
        vc_session = VcenterSession(vcenter_info)
        self.session = vc_session
        self.content = vc_session.si.content

    def get_datastore_capacity_free(self, name=None, uuid=None, moid=None):
        ds_details = None
        try:
            if name is None and uuid is None and moid is None:
                ds_details = []
                ds_objs = utils.get_objs(self.content, self.content.rootFolder, [vim.Datastore])
                for obj in ds_objs:
                    ds_detail = utils.datastore_capacity_free(obj)
                    ds_details.append(ds_detail)
            else:
                ds_obj = utils.get_datastore_moref(self.content, name=name, uuid=uuid, moid=moid)
                if ds_obj:
                    ds_details = utils.datastore_capacity_free(ds_obj)
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)
        return ds_details

    def get_vm_ip(self, name=None, uuid=None, moid=None):
        vm_detail = {}
        try:
            vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid, moid=moid)
            if vm_obj:
                vm_detail["name"] = vm_obj.summary.config.name
                vm_detail["uuid"] = vm_obj.summary.config.uuid
                vm_detail["state"] = vm_obj.summary.runtime.powerState
                vm_detail["tools_version"] = vm_obj.guest.toolsVersion
                vm_detail["guest_state"] = vm_obj.guest.guestState
                vm_detail["uptime"] = vm_obj.summary.quickStats.uptimeSeconds or 0
                vm_detail["ip"] = vm_obj.guest.ipAddress
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)
        return vm_detail

    def get_dest_folder(self, datacenter_name, vmfolder_name=None):
        """ get vm/template view folder moref
        """
        # get datacenter_obj
        datacenter_obj = utils.get_datacenter_moref(self.content, name=datacenter_name)
        if not datacenter_obj:
            raise Exception("Not found datacenter!")

        # get vm dest folder obj
        destfolder = None
        # destfolder = utils.filter_vmfolder_obj(self.content, vmfolder_name)
        if vmfolder_name:
            destfolder = utils.get_folder_obj(datacenter_obj.vmFolder, vmfolder_name.split('/'))
        if not destfolder:
            destfolder = datacenter_obj.vmFolder
        return destfolder

    def clone_vm(self, template_name, vm_name, datacenter_name, cluster_name,
                 esxi_name, res_pool_name, datastore_cluster, datastore_name,
                 vmfolder_name, num_cpu, num_core, memoryMB, poweron,
                 vm_disk, vm_net, dnslist, domain, hostname,  vm_uuid, is_template=False):
        """
        Clone a VM from a template/VM, datacenter_name, datastore_name, vm_folder
        cluster_name, resource_pool, and poweron are all optional.
        """
        # get template_obj
        template_obj = utils.get_vm_moref(self.content, name=template_name, uuid=None)
        if not template_obj:
            raise Exception("Not found template!")

        destfolder = self.get_dest_folder(datacenter_name, vmfolder_name)

        # get vm dest datastore obj
        datastore_moref = utils.get_datastore_moref(self.content, name=datastore_name)
        if not datastore_moref:
            raise Exception("Not found datastore!")

        # get cluster_obj if none git the first one
        cluster_obj = utils.get_cluster_moref(self.content, name=cluster_name)
        if not cluster_obj:
            raise Exception("Not found cluster!")

        # get esxi host obj
        esxi_moref = None
        for host_mo in cluster_obj.host:
            if host_mo.name == esxi_name:
                esxi_moref = host_mo

        # get res_pool moref
        if res_pool_name:
            res_pool_moref = utils.get_res_pool_moref(self.content, res_pool_name)
        else:
            res_pool_moref = cluster_obj.resourcePool

        # Get vm teplate system type
        sys_type = utils.get_system_type(template_obj.config)
        # Extended network pg_moref attribute
        vm_net = utils.extended_network_moref(self.content, vm_net)
        # Extended datastore ds_moref attribute
        vm_disk = utils.extended_datastore_moref(self.content, vm_disk)
        if not vm_uuid:
            vm_uuid = str(uuid.uuid1())
        # Verify vm hostname
        hostname = vmops.sanitize_hostname(vm_name, hostname)

        # make clone spec
        vmclonespec = vmops.VmCloneSpec(template_obj, sys_type, vm_uuid,
                                        vm_net, vm_disk,
                                        num_cpu, num_core, memoryMB,
                                        res_pool_moref, esxi_moref, datastore_moref,
                                        poweron, hostname, domain, dnslist, is_template)

        LOG.debug("cloning VM [%s]..." % vm_name)
        try:
            task = template_obj.Clone(name=vm_name, folder=destfolder, spec=vmclonespec.clone_spec)
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        ret_data = {"task_key": task.info.key, "name": vm_name, "uuid": vm_uuid,
                    "numCPUs": num_cpu, "numCores": num_core,
                    "memoryMB": memoryMB}
        return ret_data

    def poweroff_destroy_vm(self, name=None, uuid=None):
        """ delete vm
        """
        vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid)
        if vm_obj:
            try:
                if format(vm_obj.runtime.powerState) == "poweredOn":
                    task = vm_obj.PowerOff()
                    (ret_status, ret_str) = utils.wait_for_task(task)
                if 0 == ret_status:
                    task = vm_obj.Destroy_Task()
                    (ret_status, ret_str) = utils.wait_for_task(task)
                else:
                    ret_status = -2
            except vmodl.MethodFault as error:
                LOG.exception("Caught vmodl fault : " + error.msg)
                return -1
        else:
            ret_status = -1
        return ret_status

    def destroy_vm(self, name=None, uuid=None):
        """ delete vm
        """
        vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid)
        if vm_obj:
            try:
                task = vm_obj.Destroy_Task()
                (ret_status, ret_str) = utils.wait_for_task(task)
            except vmodl.MethodFault as error:
                LOG.exception("Caught vmodl fault : " + error.msg)
                return -1
        else:
            ret_status = -1
        return ret_status

    def poweron_vm(self, name=None, uuid=None):
        """ power on vm
        """
        try:
            vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid)
            if vm_obj:
                try:
                    task = vm_obj.PowerOn()
                except vmodl.MethodFault as error:
                    LOG.exception("Caught vmodl fault : " + error.msg)
                    return -1
                (ret_status, ret_str) = utils.wait_for_task(task)
            else:
                ret_status = -1
            return ret_status
        except Exception as ex:
            return -1

    def poweroff_vm(self, name=None, uuid=None):
        """ power off vm
        """
        try:
            vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid)
            if vm_obj:
                try:
                    task = vm_obj.PowerOff()
                except vmodl.MethodFault as error:
                    LOG.exception("Caught vmodl fault : " + error.msg)
                    return -1
                (ret_status, ret_str) = utils.wait_for_task(task)
            else:
                ret_status = -1
            return ret_status
        except Exception as ex:
            return -1

    def reboot_vm(self, name=None, uuid=None):
        """
        reboot vm
        """
        vm_obj = utils.get_vm_moref(self.content, name=name, uuid=uuid)
        if vm_obj:
            try:
                # does the actual vm reboot
                task = vm_obj.RebootGuest()
            except Exception as error:
                LOG.waiting("Caught fault : " + error)
                # forceably shutoff/on
                # need to do if vmware guestadditions isn't running
                task = vm_obj.ResetVM_Task()
            (ret_status, ret_str) = utils.wait_for_task(task)
        else:
            ret_status = -1
        return ret_status

    def get_task_result_by_key(self, task_key):
        """ get task info
        """
        task_result = {}
        task_mo = None
        try:
            recent_tasks = self.content.taskManager.recentTask
            for task in recent_tasks:
                if task_key == task.info.key:
                    task_mo = task
                    # LOG.debug("found the task: %s" % task_key)
                    break
        except Exception as error:
            LOG.exception("Caught fault : " + error)
        if task_mo:
            # No wait, waiting lead to apscheduler job num exceed maximum
            # (status, result) = utils.wait_for_task(task)
            result = task_mo.info.result
            vm_detail = None
            if result and isinstance(result, vim.VirtualMachine):
                vm_detail = vm.vm_info_json(result)
                # LOG.debug("found the task result: %s" % vm_detail)
            else:
                # 在在这种情况，任务成功，但不以获取 VM 相关信息
                pass
            task_result["vm"] = vm_detail
            task_result["state"] = task_mo.info.state
            # task_result["progress"] = 99 if task_mo.info.state == "success" else task_mo.info.progress
            task_result["progress"] = task_mo.info.progress
            if task_mo.info.error:
                task_result["progress"] = 99
                task_result["error"] = task_mo.info.error.msg
        return task_result

    def get_build_task_state(self, task_key):
        """ get task info
        """
        task_result = {}
        try:
            recent_tasks = self.content.taskManager.recentTask
            for task_mo in recent_tasks:
                if task_key != task_mo.info.key:
                    continue
                task_state = task_mo.info.state
                task_result["state"] = task_state
                task_result["progress"] = task_mo.info.progress
                if task_state == 'success':
                    task_result["vm"] = vm.vm_info_json(task_mo.info.entity)
                    task_result["progress"] = 100
                if task_mo.info.error:
                    task_result["error"] = task_mo.info.error.msg
                    task_result["progress"] = 100
                break
        except Exception as error:
            LOG.exception("Caught fault : " + error)
        return task_result

    def get_attach_disk_task_state(self, task_key, vdev_node=None):
        """ get attach disk task info
        """
        task_result = {}
        try:
            recent_tasks = self.content.taskManager.recentTask
            for task_mo in recent_tasks:
                if task_key != task_mo.info.key:
                    continue
                task_state = task_mo.info.state
                task_result["state"] = task_state
                task_result["progress"] = task_mo.info.progress
                if task_state == 'success':
                    vm_obj = task_mo.info.entity
                    if vdev_node and vm_obj:
                        task_result["disk"] = vm.get_vm_disk_device_info(vm_obj.config.hardware.device,
                                                                         vdev_node)
                    task_result["progress"] = 99
                if task_mo.info.error:
                    task_result["error"] = task_mo.info.error.msg
                    task_result["progress"] = 99
                break
        except Exception as error:
            task_result = {"progress": 99, "error": str(error)}
            LOG.exception("Caught fault : " + error)
        return task_result

    def vm_extra_config(self, vm_moid, options):
        """ add or update vm extra configure
        """
        vm_moref = utils.get_vm_moref(self.content, moid=vm_moid)
        config_spec = vmops.create_extra_config_spec(options)
        task_moref = task_utils.reconfig_vm_task(vm_moref, config_spec)
        return task_moref.info.key

    def attach_vmdk_sharing_disk(self, vm_moid, disk):
        """ attach disk to vm
        disk: {'ds_moid': 'datastore-1415', 'disk_size': 1, 'vdev_node': '1:0', 'disk_path': ''}
        """
        vm_moref = utils.get_vm_moref(self.content, moid=vm_moid)
        ds_moref = utils.get_datastore_moref(self.content, moid=disk['ds_moid'])
        config_spec = vmops.vm_add_vmdk_disk(vm_moref, ds_moref, disk, sharing=True)
        task_moref = task_utils.reconfig_vm_task(vm_moref, config_spec)
        return task_moref.info.key

    def dettach_disk(self, vm_moid, disk_file_path):
        """ attach disk from vm
        disk_file_path: '[DS5020_1] test_004/test_004_2.vmdk'
        """
        vm_moref = utils.get_vm_moref(self.content, moid=vm_moid)
        config_spec = vmops.vm_remove_vmdk_disk(vm_moref, disk_file_path)
        task_moref = task_utils.reconfig_vm_task(vm_moref, config_spec)
        return task_moref.info.key

    def attach_disks(self, vm_name, disks):
        """ attach disk to vm
        disks: [{'ds_name': 'DS5020_1', 'ds_moid': 'datastore-1415', 'disk_type': 'eagerZeroedThick', 'disk_size': 1, 'scsi_type': 'LsiLogicSAS', 'disk_file_path': ''},
               ]
        """
        utils.extended_datastore_moref(self.content, disks)
        # vm_moref = utils.get_vm_moref(self.content, uuid=vm_uuid)
        vm_moref = utils.get_vm_moref(self.content, name=vm_name)
        config_spec = vmops.create_attach_disks_config_spec(vm_moref, disks)
        task_moref = task_utils.reconfig_vm_task(vm_moref, config_spec)
        return task_moref.info.key

    def dettach_disks(self, vm_name, disks):
        """ attach disk from vm
        disks: [{disk_file_path: '[DS5020_1] test_004/test_004_2.vmdk'},
               ]
        """
        vm_moref = utils.get_vm_moref(self.content, name=vm_name)
        config_spec = vmops.create_remove_disks_config_spec(vm_moref, disks)
        task_moref = task_utils.reconfig_vm_task(vm_moref, config_spec)
        return task_moref.info.key
