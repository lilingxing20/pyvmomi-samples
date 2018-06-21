# -*- coding:utf-8 -*-

""" vm clone spec config
"""
from __future__ import absolute_import, division

from pyVmomi import vim
from . import vmops


class VmCloneSpec():
    """
    make clone spec
    """
    def __init__(self, template_moref, sys_type, vm_uuid,
                 vm_net, vm_disk, num_cpu, num_core, memoryMB,
                 res_pool_moref, esxi_moref, datastore_moref,
                 poweron, hostname, domain=None, dnslist=None,
                 is_template=False):
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
        dev_nics = vmops.get_vm_nic_adapter_dev(template_moref)
        dev_disks = vmops.get_vm_disk_dev(template_moref)
        scsi_controllers = vmops.get_vm_scsi_controller_dev(template_moref)

        nic_spec_list = vmops.config_vm_nic(dev_nics, vm_net)
        dev_changes += nic_spec_list
        (disk_spec_list, controller_spec_list) = vmops.config_vm_disk(scsi_controllers, dev_disks, vm_disk)
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
        sysprep_custom = vmops.sysprep_customization(hostname=hostname, domain=domain, sys_type=sys_type)
        custom_spec.identity = sysprep_custom

        # Make network customization
        adaptermap_custom = vmops.network_customization(vm_net)
        custom_spec.nicSettingMap = adaptermap_custom

        # Make dns customization
        dns_custom = vmops.dns_customization(dnslist)
        custom_spec.globalIPSettings = dns_custom

        return custom_spec
