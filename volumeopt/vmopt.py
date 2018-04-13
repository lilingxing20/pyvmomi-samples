#!/usr/bin/env python
# coding=utf-8

'''
Author      : lixx (https://github.com/lilingxing20)
Created Time: Thu 29 Mar 2018 03:25:37 PM CST
File Name   : volumeopt.py
Description : 
'''
from pyVmomi import vim

from oslo_log import log as logging
from oslo_utils import units

from i18n import _, _LE, _LW

import constants
import vm_util
import utils
import spec_util
import task_util


LOG = logging.getLogger(__name__)

BACKING_UUID_KEY = 'instanceUuid'
EXTRA_CONFIG_VOLUME_ID_KEY = "cinder.volume.id"

DISK_FORMAT_VMDK = 'vmdk'
DISK_FORMAT_ISCSI = 'iscsi'

SIZE_BYTES = "sizeBytes"
PROFILE_NAME = "storageProfileName"

CREATE_PARAM_BACKING_NAME = 'name'
CREATE_PARAM_TEMP_BACKING = 'temp_backing'

CREATE_PARAM_ADAPTER_TYPE = 'adapter_type'


class VMwareVmOps(object):
    """Manages vm operations. """

    def __init__(self, content, max_objects=100):
        self._content = content
        self._max_objects = max_objects
        self._folder_cache = {}

    def _get_instance_group_folder(self, dc_ref, folders):
        """Get inventory folder for organizing instance.
        :param datacenter: Reference to the datacenter
        :return: Reference to the inventory folder
        """
        folders = folders or []
        folder_names = ['Instance'] + folders

        vmfolder = dc_ref.vmFolder
        f_ref = None
        for folder_name in folder_names:
            f_ref = utils.get_child_ref_by_name(vmfolder, folder_name, vim.Folder)
            if f_ref:
                vmfolder = f_ref
            else:
                vmfolder = task_util.create_inventory_folder(vmfolder, folder_name)
        return vmfolder

    def _get_storage_profile_id(self, instance):
        pass

    def _select_ds_for_volume(self, dc_moid, cluster_moid, ds_moid,
                              host_moid=None, folders=None):
        """Select datastore that can accommodate the given vm's backing.

        Returns the selected datastore summary along with a compute host and
        its resource pool and folder where the vm can be created
        :return: (host, resource_pool, folder, summary)
        """
        dc_ref = utils.get_datacenter_moref(self._content, moid=dc_moid)
        if not dc_ref:
            LOG.error(_LE("No valid datacenter is available."))
            raise exception.NoValidDatacenter()

        resource_pool = None
        host_ref = None
        cluster_ref = utils.get_child_ref_by_moid(dc_ref.hostFolder, cluster_moid)
        if not cluster_ref:
            LOG.warn(_LW("No valid cluster is available."))
            host_ref = utils.get_child_ref_by_moid(dc_ref.hostFolder, host_moid)
            if not host_ref:
                LOG.error(_LE("No valid host is available."))
                raise exception.NoValidHost()
        else:
            resource_pool = cluster_ref.resourcePool

        host_ref = utils.get_ref_from_array_by_moid(cluster_ref.host, host_moid)
        if not host_ref:
            LOG.warn(_LW("No valid host is specified."))

        ds_ref = utils.get_ref_from_array_by_moid(cluster_ref.datastore, ds_moid)
        if not ds_ref:
            LOG.error(_LE("No valid datastore is available."))
            raise exception.NoValidDatastore()

        folder_ref = self._get_instance_group_folder(dc_ref, folders)

        return (resource_pool, host_ref, ds_ref, folder_ref)

    def create_vm(self, instance, dc_moid, cluster_moid, ds_moid,
                  host_moid=None, folders=None):
        """Create vm backing under the given host.

        If host is unspecified, any suitable host is selected.

        :param instance: Instance dict
        :param host: Reference of the host
        :return: Reference to the created backing
        """
        # instance = {"name": "vm-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 10}
        # instance = {"name": "vm-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 1,
        #             "disk_type": "thin", "adapter_type": "lsiLogicsas",
        #             "hw_version": "vmx-11", "description": "This is vm"}

        (resource_pool, host_ref, ds_ref,
                folder_ref) = self._select_ds_for_volume(dc_moid,
                                                         cluster_moid,
                                                         ds_moid,
                                                         host_moid,
                                                         folders)

        # check if a storage profile needs to be associated with the backing VM
        profile_id = self._get_storage_profile_id(instance)

        # Use vm name as the default display name.
        display_name = instance['name']
        uuid = instance['uuid']
        memory_mb = instance['memory_mb']
        vcpus = instance['vcpus']
        cores_per_socket = instance.get('cores_per_socket')
        description = instance.get('description')
        hw_version = instance.get('hw_version')
        disk_type = instance.get('disk_type', 'thin')
        size_kb = instance['size'] * units.Mi
        adapter_type = instance.get('adapter_type', 'lsiLogic')
        os_type=instance.get('os_type', 'rhel7_64Guest')
        # vif_infos = {'network_name': 'vlan222', 'network_type': 'DistributedVirtualPortgroup', 'dvpg_moid': 'dvportgroup-138', 'dvpg_uuid': '46 a3 0c 50 c0 38 6a d6-cb 12 50 01 45 7d 79 bd', 'dvs_port_key': '',  'vif_model': 'vmxnet3', 'mac_address': '00:50:56:ab:18:02',  'iface_id': 1}
        # vif_infos = {'network_name': 'vlan222', 'network_type': 'DistributedVirtualPortgroup', 'dvpg_moid': 'dvportgroup-138', 'dvpg_uuid': '46 a3 0c 50 c0 38 6a d6-cb 12 50 01 45 7d 79 bd', 'vif_model': 'vmxnet3', 'mac_address': '00:50:56:ab:18:02',  'iface_id': 1}
        # vif_infos = {'network_name': 'VM127', 'network_type': 'Network', 'dvpg_moid': 'network-530', 'vif_model': 'vmxnet3', 'mac_address': '00:50:56:ab:18:02',  'iface_id': 1}
        vif_infos = instance['vif_infos']
        create_spec = spec_util.create_vm_config_spec(display_name,
                                                      uuid,
                                                      vcpus,
                                                      memory_mb,
                                                      ds_ref.name,
                                                      vif_infos,
                                                      cores_per_socket=cores_per_socket,
                                                      hw_version=hw_version,
                                                      os_type=os_type,
                                                      profile_id=profile_id,
                                                      description=description)
        vm_ref = task_util.create_vm_task(folder_ref, resource_pool,
                                          host_ref, create_spec)
        return vm_ref

    def destroy_vm(self, instance):
        """Delete vm
        """
        # instance = {"name": "vol-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe"}
        vm_ref = utils.get_vm_moref(self._content, name=instance['name'],
                                    uuid=instance['uuid'])
        (status, info) = (-1, None)
        if vm_ref:
            (status, info) = task_util.destroy_vm_task(vm_ref)
        return status

    def list_vm(self):
        pass

    def attach_volume(self, driver_type, instance, volume, adapter_type=None):
        """Attach volume storage to VM instance."""
        # driver_volume_type: vmdk|iscsi
        # instance: {'moid': 'vm-2663', 'name': 'vol-1'}
        # volume: {'name': 'vol-1', 'moid': 'vm-2664', 'uuid': '5a60951d-6652-4c85-bad3-4350de7d308a'}
        LOG.debug("Volume attach. Driver type: %s", driver_type,
                  instance=instance)
        if driver_type == DISK_FORMAT_VMDK:
            self._attach_volume_vmdk(instance, volume, adapter_type)
#        elif driver_type == DISK_FORMAT_ISCSI:
#            self._attach_volume_iscsi(connection_info, instance, adapter_type)
        else:
            raise exception.VolumeDriverNotFound(driver_type=driver_type)

    def _attach_volume_vmdk(self, instance, volume, adapter_type=None):
        """Attach vmdk volume storage to VM instance."""
        LOG.debug("_attach_volume_vmdk: %s", volume=volume, instance=instance)
        vm_ref = utils.get_vm_moref(self._content, moid=instance['moid'])
        volume_ref = utils.get_vm_moref(self._content, moid=volume['moid'])
        volume_uuid = volume_ref.config.uuid

        # Get details required for adding disk device such as
        # adapter_type, disk_type
        vmdk = vm_util.get_vmdk_info(volume_ref)
        vmdk_path = vmdk.path
        vmdk_uuid = vmdk.device.backing.uuid
        adapter_type = adapter_type or vmdk.adapter_type

        # IDE does not support disk hotplug
        if adapter_type == constants.ADAPTER_TYPE_IDE:
            state = vm_ref.runtime.powerState
            if state.lower() != 'poweredoff':
                raise exception.Invalid(_('%s does not support disk '
                                          'hotplug.') % adapter_type)

        # Attach the disk to virtual machine instance
        self._attach_disk_to_vm(vm_ref, adapter_type, vmdk.disk_type,
                                vmdk_path=vmdk_path,
                                disk_uuid=vmdk_uuid)

        # Store the uuid of the volume_device
        self._update_volume_details(vm_ref, volume_uuid, vmdk_uuid)

        LOG.debug("Attached VMDK: %s", vmdk_path, instance=instance)

#    def _attach_volume_iscsi(self, connection_info, instance,
#                             adapter_type=None):
#        """Attach iscsi volume storage to VM instance."""
#        vm_ref = vm_util.get_vm_ref(self._session, instance)
#        # Attach Volume to VM
#        LOG.debug("_attach_volume_iscsi: %s", connection_info,
#                  instance=instance)
#
#        data = connection_info['data']
#
#        # Discover iSCSI Target
#        device_name = self._iscsi_discover_target(data)[0]
#        if device_name is None:
#            raise exception.StorageError(
#                reason=_("Unable to find iSCSI Target"))
#        if adapter_type is None:
#            # Get the vmdk file name that the VM is pointing to
#            hardware_devices = self._session._call_method(
#                vutil, "get_object_property", vm_ref, "config.hardware.device")
#            adapter_type = vm_util.get_scsi_adapter_type(hardware_devices)
#
#        self._attach_disk_to_vm(vm_ref, instance,
#                               adapter_type, 'rdmp',
#                               device_name=device_name)
#        LOG.debug("Attached ISCSI: %s", connection_info, instance=instance)


    def _attach_disk_to_vm(self, vm_ref, adapter_type, disk_type,
                           vmdk_path=None,
                           disk_uuid=None,
                           disk_size=None,
                           linked_clone=False,
                           device_name=None,
                           disk_io_limits=None):                                                                                                                                                                       
        """Attach disk to VM by reconfiguration."""
        instance_name = vm_ref.name
        (controller_key, unit_number,
         controller_spec) = vm_util.\
                 allocate_controller_key_and_unit_number(vm_ref,
                                                         adapter_type)

        vmdk_attach_config_spec = spec_util.\
                get_vmdk_attach_config_spec(disk_type, vmdk_path, disk_size,
                                            linked_clone, controller_key,
                                            unit_number, device_name,
                                            disk_uuid, disk_io_limits)
        if controller_spec:
            vmdk_attach_config_spec.deviceChange.append(controller_spec)

        LOG.debug("Reconfiguring VM instance %(instance_name)s to attach "
                  "disk %(vmdk_path)s or device %(device_name)s with type "
                  "%(disk_type)s",
                  {'instance_name': instance_name, 'vmdk_path': vmdk_path,
                   'device_name': device_name, 'disk_type': disk_type})

        task_util.reconfigure_vm(vm_ref, vmdk_attach_config_spec)
        LOG.debug("Reconfigured VM instance %(instance_name)s to attach "
                  "disk %(vmdk_path)s or device %(device_name)s with type "
                  "%(disk_type)s",
                  {'instance_name': instance_name, 'vmdk_path': vmdk_path,
                   'device_name': device_name, 'disk_type': disk_type})


    def detach_volume(self, driver_type, instance, volume):
        """Detach volume storage to VM instance."""
        # driver_volume_type: vmdk|iscsi
        # instance: {'moid': 'vm-2663', 'name': 'vol-1'}
        # volume: {'name': 'vol-1', 'moid': 'vm-2664', 'uuid': '5a60951d-6652-4c85-bad3-4350de7d308a'}
        LOG.debug("Volume detach. Driver type: %s", driver_type,
                  instance=instance)
        if driver_type == DISK_FORMAT_VMDK:
            self._detach_volume_vmdk(instance, volume)
#        elif driver_type == DISK_FORMAT_ISCSI:
#            self._detach_volume_iscsi(connection_info, instance)
        else:
            raise exception.VolumeDriverNotFound(driver_type=driver_type)

    def _detach_volume_vmdk(self, instance, volume):
        """Detach volume storage to VM instance."""
        vm_ref = utils.get_vm_moref(self._content, moid=instance['moid'])
        # Detach Volume from VM
        LOG.debug("_detach_volume_vmdk: %s", volume=volume, instance=instance)
        volume_ref = utils.get_vm_moref(self._content, moid=volume['moid'])
        volume_uuid = volume_ref.config.uuid

        import pdb;pdb.set_trace()

        device = self._get_vmdk_backed_disk_device(vm_ref, volume_ref)

        # Get disk uuid
        disk_uuid = device.backing.uuid

        # Get details required for adding disk device such as
        # adapter_type, disk_type
        vmdk = vm_util.get_vmdk_info(vm_ref, disk_uuid)

        # IDE does not support disk hotplug
        if vmdk.adapter_type == constants.ADAPTER_TYPE_IDE:
            state = vm_ref.runtime.powerState
            if state.lower() != 'poweredoff':
                raise exception.Invalid(_('%s does not support disk '
                                          'hotplug.') % vmdk.adapter_type)

        self._consolidate_vmdk_volume(instance, vm_ref, device, volume_ref,
                                      adapter_type=vmdk.adapter_type,
                                      disk_type=vmdk.disk_type)

        self.detach_disk_from_vm(vm_ref, device)
                                                                                                                                                                   
        # Remove key-value pair <volume_id, vmdk_uuid> from instance's
        # extra config. Setting value to empty string will remove the key.
        self._update_volume_details(vm_ref, volume_uuid, "")

        LOG.debug("Detached VMDK: %s", volume_uuid, instance=instance)

#    def _detach_volume_iscsi(self, connection_info, instance):
#        """Detach volume storage to VM instance."""
#        vm_ref = vm_util.get_vm_ref(self._session, instance)
#        # Detach Volume from VM
#        LOG.debug("_detach_volume_iscsi: %s", connection_info,
#                  instance=instance)
#        data = connection_info['data']
#
#        # Discover iSCSI Target
#        device_name, uuid = self._iscsi_get_target(data)
#        if device_name is None:
#            raise exception.StorageError(
#                reason=_("Unable to find iSCSI Target"))
#
#        # Get the vmdk file name that the VM is pointing to
#        hardware_devices = self._session._call_method(vutil,
#                                                      "get_object_property",
#                                                      vm_ref,
#                                                      "config.hardware.device")
#        device = vm_util.get_rdm_disk(hardware_devices, uuid)
#        if device is None:
#            raise exception.DiskNotFound(message=_("Unable to find volume"))
#        self.detach_disk_from_vm(vm_ref, instance, device, destroy_disk=True)
#        LOG.debug("Detached ISCSI: %s", connection_info, instance=instance)
#

    def _get_vmdk_backed_disk_device(self, vm_ref, volume_ref):
        # Get the vmdk file name that the VM is pointing to
        hardware_devices = vm_ref.config.hardware.device

        # Get disk uuid
        disk_device = self._get_vmdk_base_volume_device(volume_ref)
        disk_uuid = disk_device.backing.uuid

        device = vm_util.get_vmdk_backed_disk_device(hardware_devices,
                                                     disk_uuid)
        if not device:
            raise exception.DiskNotFound(message=_("Unable to find volume disk."))
        return device

    def _get_vmdk_base_volume_device(self, volume_ref):
        # Get the vmdk file name that the VM is pointing to
        hardware_devices = volume_ref.config.hardware.device
        return vm_util.get_vmdk_volume_disk(hardware_devices)

    def detach_disk_from_vm(self, vm_ref, device, destroy_disk=False):
        """Detach disk from VM by reconfiguration."""
        instance_name = vm_ref.name
        vmdk_detach_config_spec = spec_util.\
                get_vmdk_detach_config_spec(device, destroy_disk)
        disk_key = device.key
        LOG.debug("Reconfiguring VM instance %(instance_name)s to detach "
                  "disk %(disk_key)s",
                  {'instance_name': instance_name, 'disk_key': disk_key})
        task_util.reconfigure_vm(vm_ref, vmdk_detach_config_spec)
        LOG.debug("Reconfigured VM instance %(instance_name)s to detach "
                  "disk %(disk_key)s",
                  {'instance_name': instance_name, 'disk_key': disk_key})

    def _consolidate_vmdk_volume(self, instance, vm_ref, device, volume_ref,
                                 adapter_type=None, disk_type=None):
        """Consolidate volume backing VMDK files if needed.

        The volume's VMDK file attached to an instance can be moved by SDRS
        if enabled on the cluster.
        By this the VMDK files can get copied onto another datastore and the
        copy on this new location will be the latest version of the VMDK file.
        So at the time of detach, we need to consolidate the current backing
        VMDK file with the VMDK file in the new location.

        We need to ensure that the VMDK chain (snapshots) remains intact during
        the consolidation. SDRS retains the chain when it copies VMDK files
        over, so for consolidation we relocate the backing with move option
        as moveAllDiskBackingsAndAllowSharing and then delete the older version
        of the VMDK file attaching the new version VMDK file.

        In the case of a volume boot the we need to ensure that the volume
        is on the datastore of the instance.
        """

        original_device = self._get_vmdk_base_volume_device(volume_ref)

        original_device_path = original_device.backing.fileName
        current_device_path = device.backing.fileName

        if original_device_path == current_device_path:
            # The volume is not moved from its original location.
            # No consolidation is required.
            LOG.debug("The volume has not been displaced from "
                      "its original location: %s. No consolidation "
                      "needed.", current_device_path)
            return

        # The volume has been moved from its original location.
        # Need to consolidate the VMDK files.
        LOG.info(_LI("The volume's backing has been relocated to %s. Need to "
                     "consolidate backing disk file."), current_device_path)

        # Pick the host and resource pool on which the instance resides.
        # Move the volume to the datastore where the new VMDK file is present.
        host = vm_ref.runtime.host
        res_pool = host.parent.resourcePool
        datastore = device.backing.datastore
        detached = False
        LOG.debug("Relocating volume's backing: %(backing)s to resource "
                  "pool: %(rp)s, datastore: %(ds)s, host: %(host)s.",
                  {'backing': volume_ref, 'rp': res_pool, 'ds': datastore,
                   'host': host})
        try:
            self._relocate_vmdk_volume(volume_ref, res_pool, datastore, host)
        except exception.FileNotFound:
            # Volume's vmdk was moved; remove the device so that we can
            # relocate the volume.
            LOG.warn(_LW("Virtual disk: %s of volume's backing not found."),
                     original_device_path, exc_info=True)
            LOG.debug("Removing disk device of volume's backing and "
                      "reattempting relocate.")
            self.detach_disk_from_vm(volume_ref, instance, original_device)
            detached = True
            self._relocate_vmdk_volume(volume_ref, res_pool, datastore, host)

        # Volume's backing is relocated now; detach the old vmdk if not done
        # already.
        if not detached:
            self.detach_disk_from_vm(volume_ref, instance, original_device,
                                     destroy_disk=True)

        # Attach the current volume to the volume_ref
        self._attach_disk_to_vm(volume_ref, instance,
                               adapter_type, disk_type,
                               vmdk_path=current_device_path)

    def _update_volume_details(self, vm_ref, volume_uuid, device_uuid):
        # Store the uuid of the volume_device
        volume_option = 'volume-%s' % volume_uuid
        extra_opts = {volume_option: device_uuid}

        extra_config_specs = spec_util.get_vm_extra_config_spec(extra_opts)
        task_util.reconfigure_vm(vm_ref, extra_config_specs)

