# -*- coding:utf-8 -*-

import logging

from pyVmomi import vim, vmodl

import session
from tools import cluster, datacenter, esxi, network, storage, utils, vm

LOG = logging.getLogger(__name__)


class VMwareClient(session.VMwareSession):
    """
    vmware client
    """
    def __init__(self, host, user, pwd, port=443):
        super(VMwareClient, self).__init__(host=host,
                                           user=user,
                                           pwd=pwd,
                                           port=port)
        self.content = self.si.RetrieveContent()

    def get_datacenter_detail(self):
        """
        """
        dc_detail = []
        try:
            dc_objs = utils.get_objs(self.content, self.content.rootFolder, [vim.Datacenter])
            for obj in dc_objs:
                dc_info = datacenter.get_datacenter_detail(self.content, obj)
                dc_detail.append(dc_info)
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)
        return dc_detail

    def vcenter_details(self):
        """
        get vcenter details
        @ object_view.view:
        @@  <class 'pyVmomi.VmomiSupport.vim.ClusterComputeResource'>
        @@  <class 'pyVmomi.VmomiSupport.vim.Datacenter'>
        @@  <class 'pyVmomi.VmomiSupport.vim.Datastore'>
        @@  <class 'pyVmomi.VmomiSupport.vim.dvs.DistributedVirtualPortgroup'>
        @@  <class 'pyVmomi.VmomiSupport.vim.dvs.VmwareDistributedVirtualSwitch'>
        @@  <class 'pyVmomi.VmomiSupport.vim.Folder'>
        @@  <class 'pyVmomi.VmomiSupport.vim.HostSystem'>
        @@  <class 'pyVmomi.VmomiSupport.vim.Network'>
        @@  <class 'pyVmomi.VmomiSupport.vim.ResourcePool'>
        @@  <class 'pyVmomi.VmomiSupport.vim.StoragePod'>
        @@  <class 'pyVmomi.VmomiSupport.vim.VirtualApp'>
        @@  <class 'pyVmomi.VmomiSupport.vim.VirtualMachine'>
        """
        vc_details = {"vm": [],
                      "vapp": [],
                      "storagePod": [],
                      "resourcePool": [],
                      "network": [],
                      "esxi": [],
                      "datastore": [],
                      "datacenter": [],
                      "cluster": [],
                      }
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder, [], True)
            for obj in object_view.view:
                if isinstance(obj, vim.VirtualMachine):
                    vm_detail = vm.vm_info_json(obj)
                    vc_details['vm'].append(vm_detail)

                elif isinstance(obj, vim.StoragePod):
                    pod_detail = storage.storage_pod_info_json(obj)
                    vc_details['storagePod'].append(pod_detail)

                elif isinstance(obj, vim.Datastore):
                    ds_detail = storage.datastore_info_json(obj)
                    vc_details['datastore'].append(ds_detail)

                elif isinstance(obj, vim.Network):
                    net_detail = network.network_info_json(obj)
                    vc_details['network'].append(net_detail)

                elif isinstance(obj, vim.HostSystem):
                    esxi_detail = esxi.esxi_info_json(obj)
                    vc_details['esxi'].append(esxi_detail)

                elif isinstance(obj, vim.ClusterComputeResource):
                    cluster_detail = cluster.cluster_info_json(obj)
                    vc_details['cluster'].append(cluster_detail)

                elif isinstance(obj, vim.ResourcePool):
                    pool_detail = cluster.resource_pool_info_json(obj)
                    vc_details['resourcePool'].append(pool_detail)

                elif isinstance(obj, vim.VirtualApp):
                    vapp_detail = cluster.vapp_info_json(obj)
                    vc_details['vapp'].append(vapp_detail)

                elif isinstance(obj, vim.Datacenter):
                    dc_detail = cluster.datacenter_info_json(obj)
                    vc_details['datacenter'].append(dc_detail)

            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return vc_details

    def vm_details(self):
        vm_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.VirtualMachine],
                                                                       True)
            for obj in object_view.view:
                vm_details[obj.name] = vm.vm_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return vm_details

    def vapp_details(self):
        vapp_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.VirtualApp],
                                                                       True)
            for obj in object_view.view:
                vapp_details[obj.name] = cluster.vapp_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return vapp_details

    def datastore_details(self):
        ds_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.Datastore],
                                                                       True)
            for obj in object_view.view:
                ds_details[obj.name] = storage.datastore_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return ds_details

    def datacenter_details(self):
        dc_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.Datacenter],
                                                                       True)
            for obj in object_view.view:
                dc_details[obj.name] = cluster.datacenter_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return dc_details

    def resource_pool_details(self):
        res_pool_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.ResourcePool],
                                                                       True)
            for obj in object_view.view:
                rp_val = cluster.resource_pool_info_json(obj)
                rp_key = "%s:%s" % (rp_val['owner_cluster'], rp_val['name'])
                res_pool_details[rp_key] = rp_val
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return res_pool_details

    def esxi_details(self):
        esxi_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.HostSystem],
                                                                       True)
            for obj in object_view.view:
                esxi_details[obj.name] = esxi.esxi_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return esxi_details

    def network_details(self):
        net_details = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.Network],
                                                                       True)
            for obj in object_view.view:
                net_details[obj.name] = network.network_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return net_details

    def get_vm_template(self):
        templates = {}
        try:
            object_view = self.content.viewManager.CreateContainerView(self.content.rootFolder,
                                                                       [vim.VirtualMachine],
                                                                       True)
            for obj in object_view.view:
                vm_info = vm.vm_info_json(obj)
                if vm_info.get('is_template'):
                    templates[obj.name] = vm.vm_info_json(obj)
            object_view.Destroy()
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        return templates

    def get_vm_template_by_name(self, template_name):
        return self.get_vm_by_name(template_name)

    def get_vm_by_name(self, vm_name):
        vm_details = {}
        if vm_name:
            vm_obj = utils.get_obj(self.content, [vim.VirtualMachine], vm_name)
            vm_details = vm.vm_info_json(vm_obj)
        return vm_details

    def clone_vm(self, template_name, vm_name, datacenter_name, cluster_name,
                 res_pool_name, datastore_cluster, datastore_name, vmfolder_name,
                 disktype, disksize, cpunum, corenum, memoryMB, poweron, vm_net,
                 dnslist, domain, hostname, is_template=False):
        """
        Clone a VM from a template/VM, datacenter_name, datastore_name, vm_folder
        cluster_name, resource_pool, and poweron are all optional.
        """
        # get template_obj if none git the first one
        template_obj = utils.get_obj(self.content, [vim.VirtualMachine], template_name)

        # get datacenter_obj if none git the first one
        datacenter_obj = utils.filter_datacenter_obj(self.content, datacenter_name)

        # get vm dest folder obj
        destfolder = utils.filter_vmfolder_obj(self.content, vmfolder_name)
        if not destfolder:
            destfolder = datacenter_obj.vmFolder

        # get vm dest folder obj
        if not datastore_name:
            datastore_name = template_obj.datastore[0].info.name
        datastore_obj = utils.filter_datastore_obj(self.content, datastore_name)

        # get cluster_obj if none git the first one
        cluster_obj = utils.filter_cluster_obj(self.content, cluster_name)

        # get res_pool_obj
        if res_pool_name:
            res_pool_obj = utils.get_obj(self.content, [vim.ResourcePool], res_pool_name)
        else:
            res_pool_obj = cluster_obj.resourcePool

        # get network config
        adaptermaplist = vm.config_vm_network(vm_net)
        # get dns list
        dnslist = vm.config_vm_dns(dnslist)
        # get vm teplate system type
        sys_type = utils.get_system_type(template_obj.config)
        # get vm hostname config
        if not hostname:
            hostname = vm_name
        identity = vm.config_vm_sysprep(hostname=hostname, domain=domain, sys_type=sys_type)
        # get nic mo
        for n in vm_net:
            n_mo = utils.get_network_obj(self.content, n.get('net_name'))
            if n_mo:
                n['nic'] = n_mo
        # get vm system\disk config
        vm_conf = vm.update_vm_config(template_obj, vm_net, disktype, disksize, cpunum, corenum, memoryMB)
        # get vm relocate spec
        relospec = vm.create_relospec(res_pool_obj, datastore_obj, disktype)
        # get custom spec
        customspec = vm.create_vm_customspec(adaptermap=adaptermaplist, globalip=dnslist, identity=identity)
        # get vm clone spec
        vmclonespec = vm.create_clonespec(relospec, customspec, vm_conf, poweron, is_template)

        LOG.debug("cloning VM [%s]..." % vm_name)
        try:
            task = template_obj.Clone(name=vm_name, folder=destfolder, spec=vmclonespec)
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

        ret_data = {"task_key": task.info.key, "name": vm_name, "uuid": vm_conf.uuid, "memoryMB": vm_conf.memoryMB,
                    "numCPUs": vm_conf.numCPUs, "numCores": vm_conf.numCoresPerSocket}
        return ret_data

    def delete_vm_by_name(self, vm_name):
        """
        delete vm
        """
        vm_obj = utils.filter_vm_obj(self.content, vm_name)
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
        else:
            ret_status = -1
        return ret_status

    def poweron_vm_by_name(self, vm_name):
        """
        power on vm
        """
        vm_obj = utils.filter_vm_obj(self.content, vm_name)
        if vm_obj:
            try:
                task = vm_obj.PowerOn()
            except vmodl.MethodFault as error:
                LOG.exception("Caught vmodl fault : " + error.msg)
            (ret_status, ret_str) = utils.wait_for_task(task)
        else:
            ret_status = -1
        return ret_status

    def poweroff_vm_by_name(self, vm_name):
        """
        power off vm
        """
        vm_obj = utils.filter_vm_obj(self.content, vm_name)
        if vm_obj:
            try:
                task = vm_obj.PowerOff()
            except vmodl.MethodFault as error:
                LOG.exception("Caught vmodl fault : " + error.msg)
            (ret_status, ret_str) = utils.wait_for_task(task)
        else:
            ret_status = -1
        return ret_status

    def get_task_info_by_key(self, task_key):
        """
        get task info
        """
        task_info = {}
        if not task_key:
            return task_key
        task_mo = None
        try:
            recent_tasks = self.content.taskManager.recentTask
            for task in recent_tasks:
                if task_key == task.info.key:
                    task_mo = task
                    break
        except Exception, error:
            LOG.exception("Caught fault : " + error)
        if task_mo:
            task_info["state"] = task_mo.info.state
            task_info["progress"] = task_mo.info.progress
            task_info["result"] = task_mo.info.result
            if task_mo.info.error:
                task_info["error"] = task_mo.info.error.msg
            else:
                task_info["error"] = None
            task_info["result"] = task_mo.info.result
        return task_info

    def get_task_result_by_key(self, task_key):
        """
        get task info
        """
        task_result = {}
        if not task_key:
            return task_key
        task_mo = None
        try:
            recent_tasks = self.content.taskManager.recentTask
            for task in recent_tasks:
                if task_key == task.info.key:
                    task_mo = task
                    break
        except Exception, error:
            LOG.exception("Caught fault : " + error)
        if task_mo:
            (status, result) = utils.wait_for_task(task)
            vm_detail = None
            if result and isinstance(result, vim.VirtualMachine):
                vm_detail = vm.vm_info_json(result)
            task_result["vm"] = vm_detail
            task_result["state"] = task_mo.info.state
            if task_mo.info.error:
                task_result["error"] = task_mo.info.error.msg
        return task_result
