# -*- coding:utf-8 -*-

from pyVmomi import vim
from pyVmomi import vmodl

import session

from tools import vm
from tools import cluster
from tools import storage
from tools import network
from tools import esxi
from tools import utils

import logging
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
                 is_template=False):
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
        adaptermaplist = self._vm_network(vm_net)
        # get dns list
        dnslist = self._vm_dns(dnslist=dnslist)
        # get vm hostname config
        identity = self._vm_hostname(domain=domain, hostname=hostname)
        # get customspec
        customspec = self._vm_customspec(adaptermap=adaptermaplist, globalip=dnslist, identity=identity)
        # get vm config
        vm_conf = self._vm_config(disktype, disksize, cpunum, corenum, memoryMB)
        # get vm clone spec
        vmclonespec = self._cloneSpec(customspec, vm_conf, res_pool_obj, datastore_obj, poweron, is_template)

        LOG.debug("cloning VM [%s]..." % vm_name)
        try:
            task = template_obj.Clone(name=vm_name, folder=destfolder, spec=vmclonespec)
        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)
        (ret_status, ret_str) = utils.wait_for_task(task)

        return ret_status

    def _vm_network(self, vm_net):
        """
        VM network setting
        """
        adaptermaplist=[]
        for net in vm_net:
            adaptermap = vim.vm.customization.AdapterMapping()
            fixedip = vim.vm.customization.FixedIp(ipAddress=net.ip)
            adaptermap.adapter = vim.vm.customization.IPSettings(ip=fixedip,
                                                                 subnetMask=net.netmask,
                                                                 gateway=net.gateway)
            adaptermaplist.append(adaptermap)
        return adaptermaplist

    def _vm_dns(self, dnslist):
        """
        dnslist = ['10.1.10.14', '10.1.10.15']
        """
        return vim.vm.customization.GlobalIPSettings(dnsServerList=dnslist)


    def _vm_hostname(self, domain, hostname):
        """
        hostname setting
        """
        fixedname = vim.vm.customization.FixedName(name=hostname)
        return vim.vm.customization.LinuxPrep(domain=domain,
                                              hostName=fixedname)

    def _vm_customspec(self, adaptermap, globalip, identity):
        """
        Creating vm custom spec
        """
        customspec = vim.vm.customization.Specification(nicSettingMap=adaptermap,
                                                        globalIPSettings=globalip,
                                                        identity=identity)
        return customspec

    def _vm_config(self, disktype, disksize, cpunum=1, corenum=1, memoryMB=512):
        """
        CPU/Mem
        mem = 512 #M
        vim.vm.ConfigSpec(numCPUs=1, memoryMB=mem)

        vim.vm.device.VirtualDiskSpec
        """
        vm_conf = vim.vm.ConfigSpec()
        vm_conf.numCPUs = cpu_num
        vm_conf.numCoresPerSocket = core_num
        vm_conf.memoryMB = memoryMB

        return vm_conf

    def _clonespec(self, customspec, vm_conf, res_pool_obj, datastore_obj,
                   poweron, is_template):
        """
        Create clone spec
        """
        # set ReloSpec
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore_obj
        relospec.pool = res_pool_obj

        # set CloneSpec
        clonespec = vim.vm.CloneSpec()
        clonespec.location = relospec
        clonespec.powerOn = poweron
        clonespec.template = is_template
        clonespec.customization = customspec
        clonespec.config = vm_conf

        return clonespec
