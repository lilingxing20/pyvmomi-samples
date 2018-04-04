#!/usr/bin/env python
# coding=utf-8

'''
Author      : lixx (https://github.com/lilingxing20)
Created Time: Thu 29 Mar 2018 03:25:37 PM CST
File Name   : volumeopt.py
Description : 
'''
from pyVim import connect
from pyVmomi import vim

from oslo_log import log as logging
from oslo_utils import units

from i18n import _, _LE, _LW

import constants
import vm_util
import utils


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

class VirtualDiskType(object):
    """Supported virtual disk types."""

    EAGER_ZEROED_THICK = "eagerZeroedThick"
    PREALLOCATED = "preallocated"
    THIN = "thin"

    # thick in extra_spec means lazy-zeroed thick disk
    EXTRA_SPEC_DISK_TYPE_DICT = {'eagerZeroedThick': EAGER_ZEROED_THICK,
                                 'thick': PREALLOCATED,
                                 'thin': THIN
                                 }

    @staticmethod
    def is_valid(extra_spec_disk_type):
        """Check if the given disk type in extra_spec is valid.

        :param extra_spec_disk_type: disk type in extra_spec
        :return: True if valid
        """
        return (extra_spec_disk_type in
                VirtualDiskType.EXTRA_SPEC_DISK_TYPE_DICT)

    @staticmethod
    def validate(extra_spec_disk_type):
        """Validate the given disk type in extra_spec.

        This method throws an instance of InvalidDiskTypeException if the given
        disk type is invalid.

        :param extra_spec_disk_type: disk type in extra_spec
        :raises: InvalidDiskTypeException
        """
        if not VirtualDiskType.is_valid(extra_spec_disk_type):
            raise vmdk_exceptions.InvalidDiskTypeException(
                disk_type=extra_spec_disk_type)

    @staticmethod
    def get_virtual_disk_type(extra_spec_disk_type):
        """Return disk type corresponding to the extra_spec disk type.

        :param extra_spec_disk_type: disk type in extra_spec
        :return: virtual disk type
        :raises: InvalidDiskTypeException
        """
        VirtualDiskType.validate(extra_spec_disk_type)
        return (VirtualDiskType.EXTRA_SPEC_DISK_TYPE_DICT[                                                                                                                                                                             
                extra_spec_disk_type])



class VirtualDiskAdapterType(object):
    """Supported virtual disk adapter types."""

    LSI_LOGIC = "lsiLogic"
    BUS_LOGIC = "busLogic"
    LSI_LOGIC_SAS = "lsiLogicsas"
    PARA_VIRTUAL = "paraVirtual"
    IDE = "ide"

    @staticmethod
    def is_valid(adapter_type):
        """Check if the given adapter type is valid.

        :param adapter_type: adapter type to check
        :return: True if valid
        """
        return adapter_type in [VirtualDiskAdapterType.LSI_LOGIC,
                                VirtualDiskAdapterType.BUS_LOGIC,
                                VirtualDiskAdapterType.LSI_LOGIC_SAS,
                                VirtualDiskAdapterType.PARA_VIRTUAL,
                                VirtualDiskAdapterType.IDE]

    @staticmethod
    def validate(extra_spec_adapter_type):
        """Validate the given adapter type in extra_spec.

        This method throws an instance of InvalidAdapterTypeException if the
        given adapter type is invalid.

        :param extra_spec_adapter_type: adapter type in extra_spec
        :raises: InvalidAdapterTypeException
        """
        if not VirtualDiskAdapterType.is_valid(extra_spec_adapter_type):
            raise vmdk_exceptions.InvalidAdapterTypeException(
                invalid_type=extra_spec_adapter_type)

    @staticmethod
    def get_adapter_type(extra_spec_adapter):
        """Get the adapter type to be used in VirtualDiskSpec.

        :param extra_spec_adapter: adapter type in the extra_spec
        :return: adapter type to be used in VirtualDiskSpec
        """
        VirtualDiskAdapterType.validate(extra_spec_adapter)
        # We set the adapter type as lsiLogic for lsiLogicsas/paraVirtual
        # since it is not supported by VirtualDiskManager APIs. This won't
        # be a problem because we attach the virtual disk to the correct
        # controller type and the disk adapter type is always resolved using
        # its controller key.
        if (extra_spec_adapter == VirtualDiskAdapterType.LSI_LOGIC_SAS or
                extra_spec_adapter == VirtualDiskAdapterType.PARA_VIRTUAL):
            return VirtualDiskAdapterType.LSI_LOGIC
        else:
            return extra_spec_adapter


class ControllerType(object):
    """Encapsulate various controller types."""

    LSI_LOGIC = vim.vm.device.VirtualLsiLogicController
    BUS_LOGIC = vim.vm.device.VirtualBusLogicController
    LSI_LOGIC_SAS = vim.vm.device.VirtualLsiLogicSASController
    PARA_VIRTUAL = vim.vm.device.ParaVirtualSCSIController
    IDE = vim.vm.device.VirtualIDEController

    CONTROLLER_TYPE_DICT = {
        VirtualDiskAdapterType.LSI_LOGIC: LSI_LOGIC,
        VirtualDiskAdapterType.BUS_LOGIC: BUS_LOGIC,
        VirtualDiskAdapterType.LSI_LOGIC_SAS: LSI_LOGIC_SAS,
        VirtualDiskAdapterType.PARA_VIRTUAL: PARA_VIRTUAL,
        VirtualDiskAdapterType.IDE: IDE}

    @staticmethod
    def get_controller_type(adapter_type):
        """Get the disk controller type based on the given adapter type.

        :param adapter_type: disk adapter type
        :return: controller type corresponding to the given adapter type
        :raises: InvalidAdapterTypeException
        """
        if adapter_type in ControllerType.CONTROLLER_TYPE_DICT:
            return ControllerType.CONTROLLER_TYPE_DICT[adapter_type]
        raise vmdk_exceptions.InvalidAdapterTypeException(
            invalid_type=adapter_type)

    @staticmethod
    def is_scsi_controller(controller_type):
        """Check if the given controller is a SCSI controller.

        :param controller_type: controller type
        :return: True if the controller is a SCSI controller
        """
        return controller_type in [ControllerType.LSI_LOGIC,
                                   ControllerType.BUS_LOGIC,
                                   ControllerType.LSI_LOGIC_SAS,
                                   ControllerType.PARA_VIRTUAL]


class VMwareVolumeOps(object):
    """Manages volume operations. """

    def __init__(self, content, max_objects=100):
        self._content = content
        self._max_objects = max_objects
        self._folder_cache = {}

    # TODO(vbala): move this method to datastore module
    def _is_usable(self, mount_info):
        """Check if a datastore is usable as per the given mount info.

        The datastore is considered to be usable for a host only if it is
        writable, mounted and accessible.

        :param mount_info: Host mount information
        :return: True if datastore is usable
        """
        writable = mount_info.accessMode == 'readWrite'
        # If mounted attribute is not set, then default is True
        mounted = getattr(mount_info, 'mounted', True)
        # If accessible attribute is not set, then default is False
        accessible = getattr(mount_info, 'accessible', False)

        return writable and mounted and accessible

    def get_datastore_moref(self, ds_name):
        """
        :param name: datastore name (str)
        :return: DataStore object by datastore name if found
        """
        ds_moref = None
        container = self._content.viewManager.CreateContainerView(content.rootFolder,
                                                            [vim.Datastore],
                                                            True)
        if name is not None:
            for o in container.view:
                if o.name == name:
                    ds_moref = o
                    break
        container.Destroy()
        return ds_moref

    def get_connected_hosts(self, datastore):
        """Get all the hosts to which the datastore is connected and usable.

        The datastore is considered to be usable for a host only if it is
        writable, mounted and accessible.

        :param datastore: Reference to the datastore entity
        :return: List of managed object references of all connected
                 hosts
        """
        ds_moref = self.get_datastore_moref(datastore)
        if ds_moref and not summary.accessible:
            return []

        connected_hosts = []
        for host_mount in ds_moref.host:
            if not host_mount.mountInfo:
                continue
            if self._is_usable(host_mount.mountInfo):
                connected_hosts.append(host_mount)

        return connected_hosts

    def _create_controller_config_spec(self, adapter_type):
        """Returns config spec for adding a disk controller."""
    
        controller_type = ControllerType.get_controller_type(adapter_type)
        controller_device = controller_type()
        controller_device.key = -100
        controller_device.busNumber = 0
        if ControllerType.is_scsi_controller(controller_type):
            controller_device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing('noSharing')
    
        controller_spec = vim.vm.device.VirtualDeviceSpec()
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller_spec.device = controller_device
        return controller_spec

    def _create_disk_backing(self, disk_type, vmdk_ds_file_path):
        """Creates file backing for virtual disk."""

        disk_device_bkng = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()

        if disk_type == VirtualDiskType.EAGER_ZEROED_THICK:
            disk_device_bkng.eagerlyScrub = True
        elif disk_type == VirtualDiskType.THIN:
            disk_device_bkng.thinProvisioned = True

        disk_device_bkng.fileName = vmdk_ds_file_path or ''
        disk_device_bkng.diskMode = 'persistent'

        return disk_device_bkng

    def _create_virtual_disk_config_spec(self, size_kb, disk_type,
                                         controller_key, profile_id,
                                         vmdk_ds_file_path):
        """Returns config spec for adding a virtual disk."""

        disk_device = vim.vm.device.VirtualDisk()
        # disk size should be at least 1024KB
        disk_device.capacityInKB = max(units.Ki, int(size_kb))
        if controller_key < 0:
            disk_device.key = controller_key - 1
        else:
            disk_device.key = -101
        disk_device.unitNumber = 0
        disk_device.controllerKey = controller_key
        disk_device.backing = self._create_disk_backing(disk_type,
                                                        vmdk_ds_file_path)

        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        if vmdk_ds_file_path is None:
            disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
        disk_spec.device = disk_device
        if profile_id:
            disk_profile = vim.vm.ProfileSpec()
            disk_profile.profileId = profileId
            disk_spec.profile = [disk_profile]

        return disk_spec

    def _create_specs_for_disk_add(self, size_kb, disk_type, adapter_type,
                                   profile_id, vmdk_ds_file_path=None):
        """Create controller and disk config specs for adding a new disk.

        :param size_kb: disk size in KB
        :param disk_type: disk provisioning type
        :param adapter_type: disk adapter type
        :param profile_id: storage policy profile identification
        :param vmdk_ds_file_path: Optional datastore file path of an existing
                                  virtual disk. If specified, file backing is
                                  not created for the virtual disk.
        :return: list containing controller and disk config specs
        """
        controller_spec = None
        if adapter_type == 'ide':
            # For IDE disks, use one of the default IDE controllers (with keys
            # 200 and 201) created as part of backing VM creation.
            controller_key = 200
        else:
            controller_spec = self._create_controller_config_spec(adapter_type)
            controller_key = controller_spec.device.key

        disk_spec = self._create_virtual_disk_config_spec(size_kb,
                                                          disk_type,
                                                          controller_key,
                                                          profile_id,
                                                          vmdk_ds_file_path)
        specs = [disk_spec]
        if controller_spec is not None:
            specs.append(controller_spec)
        return specs

    def _create_spec_for_disk_remove(self, disk_device):
        cf = self._session.vim.client.factory
        disk_spec = cf.create('ns0:VirtualDeviceConfigSpec')
        disk_spec.operation = 'remove'
        disk_spec.device = disk_device
        return disk_spec

    def _get_extra_config_option_values(self, extra_config):
    
        option_values = []
    
        for key, value in extra_config.items():
            opt = vim.option.OptionValue()
            opt.key = key
            opt.value = value
            option_values.append(opt)
    
        return option_values

    def _get_create_spec_disk_less(self, name, ds_name, profileId=None,
                                   extra_config=None):
        """Return spec for creating disk-less backing.

        :param name: Name of the backing
        :param ds_name: Datastore name where the disk is to be provisioned
        :param profileId: Storage profile ID for the backing
        :param extra_config: Key-value pairs to be written to backing's
                             extra-config
        :return: Spec for creation
        """
        vm_file_info = vim.vm.FileInfo()
        vm_file_info.vmPathName = '[%s]' % ds_name

        create_spec = vim.vm.ConfigSpec()
        create_spec.name = name
        create_spec.guestId = 'otherGuest'
        create_spec.numCPUs = 1
        create_spec.memoryMB = 128
        create_spec.files = vm_file_info
        # Set the hardware version to a compatible version supported by
        # vSphere 5.0. This will ensure that the backing VM can be migrated
        # without any incompatibility issues in a mixed cluster of ESX hosts
        # with versions 5.0 or above.
        create_spec.version = "vmx-08"

        if profileId:
            vmProfile = vim.vm.ProfileSpec()
            vmProfile.profileId = profileId
            create_spec.vmProfile = [vmProfile]

        if extra_config:
            if BACKING_UUID_KEY in extra_config:
                create_spec.instanceUuid = extra_config.pop(BACKING_UUID_KEY)
            create_spec.extraConfig = self._get_extra_config_option_values(
                extra_config)

        return create_spec

    def get_create_spec(self, name, size_kb, disk_type, ds_name,
                        profile_id=None, adapter_type='lsiLogic',
                        extra_config=None):
        """Return spec for creating backing with a single disk.
    
        :param name: name of the backing
        :param size_kb: disk size in KB
        :param disk_type: disk provisioning type
        :param ds_name: datastore name where the disk is to be provisioned
        :param profile_id: storage policy profile identification
        :param adapter_type: disk adapter type
        :param extra_config: key-value pairs to be written to backing's
                             extra-config
        :return: spec for creation
        """
        create_spec = self._get_create_spec_disk_less(
            name, ds_name, profileId=profile_id, extra_config=extra_config)
        create_spec.deviceChange = self._create_specs_for_disk_add(
            size_kb, disk_type, adapter_type, profile_id)
        return create_spec

    def _create_backing_int(self, folder, resource_pool, host, create_spec):
        """Helper for create backing methods."""
        LOG.debug("Creating volume backing with spec: %s.", create_spec)
        task = folder.CreateVM_Task(config=create_spec,
                                    pool=resource_pool,
                                    host=host)
        (task_state, task_info) = vm_util.wait_for_task(task)
        backing = task_info.result
        if task_state:
            LOG.info("Successfully created volume backing: %s.", backing)
        else:
            LOG.info("Created volume backing error !")
        return backing

    def create_backing(self, name, size_kb, disk_type, folder, resource_pool,
                       host, ds_name, profileId=None, adapter_type='lsiLogic',
                       extra_config=None):
        """Create backing for the volume.

        Creates a VM with one VMDK based on the given inputs.

        :param name: Name of the backing
        :param size_kb: Size in KB of the backing
        :param disk_type: VMDK type for the disk
        :param folder: Folder, where to create the backing under
        :param resource_pool: Resource pool reference
        :param host: Host reference
        :param ds_name: Datastore name where the disk is to be provisioned
        :param profile_id: Storage profile ID to be associated with backing
        :param adapter_type: Disk adapter type
        :param extra_config: Key-value pairs to be written to backing's
                             extra-config
        :return: Reference to the created backing entity
        """
        LOG.debug("Creating volume backing with name: %(name)s "
                  "disk_type: %(disk_type)s size_kb: %(size_kb)s "
                  "adapter_type: %(adapter_type)s profileId: %(profile)s at "
                  "folder: %(folder)s resource_pool: %(resource_pool)s "
                  "host: %(host)s datastore_name: %(ds_name)s.",
                  {'name': name, 'disk_type': disk_type, 'size_kb': size_kb,
                   'folder': folder, 'resource_pool': resource_pool,
                   'ds_name': ds_name, 'profile': profileId, 'host': host,
                   'adapter_type': adapter_type})

        create_spec = self.get_create_spec(
            name, size_kb, disk_type, ds_name, profile_id=profileId,
            adapter_type=adapter_type, extra_config=extra_config)
        return self._create_backing_int(folder, resource_pool, host,
                                        create_spec)

    def create_inventory_folder(self, folder_ref, new_folder_name):
        try:
            vmfolder = folder_ref.CreateFolder(new_folder_name)
        except vim.fault.DuplicateName:
            LOG.error('Another object in the same folder has the target name.')
        except vim.fault.InvalidName:
            LOG.error(_LE('The new folder name (%s) is not a valid entity name.'), new_folder_name)
        return vmfolder

    def _get_volume_group_folder(self, dc_ref, folders):
        """Get inventory folder for organizing volume backings.

        The inventory folder for organizing volume backings has the following
        hierarchy:
               <Datacenter_vmFolder>/OpenStack/Project (<project_id>)/
               <volume_folder>
        where volume_folder is the vmdk driver config option
        "vmware_volume_folder".

        :param datacenter: Reference to the datacenter
        :param project_id: OpenStack project ID
        :return: Reference to the inventory folder
        """
        folders = folders or []
        volume_folder_name = 'Volumes'
        folder_names = [volume_folder_name] + folders

        vmfolder = dc_ref.vmFolder
        f_ref = None
        for folder_name in folder_names:
            f_ref = utils.get_child_entity_by_name(vmfolder, folder_name, vim.Folder)
            if f_ref:
                vmfolder = f_ref
            else:
                vmfolder = self.create_inventory_folder(vmfolder, folder_name)
        return vmfolder

    def _select_ds_for_volume(self, volume, dc_moid, cluster_moid, ds_moid, host_moid=None, folders=None):
        """Select datastore that can accommodate the given volume's backing.

        Returns the selected datastore summary along with a compute host and
        its resource pool and folder where the volume can be created
        :return: (host, resource_pool, folder, summary)
        """
        dc_ref = utils.get_datacenter_moref(self._content, moid=dc_moid)
        if not dc_ref:
            LOG.error(_LE("No valid datacenter is available."))
            raise exception.NoValidCluster()

        cluster_ref = utils.get_child_entity_by_moid(dc_ref.hostFolder, cluster_moid)
        if not cluster_ref:
            LOG.error(_LE("No valid cluster is available."))
            raise exception.NoValidCluster()
        resource_pool = cluster_ref.resourcePool

        host_ref = None
        if host_moid:
            for _ref in cluster_ref.host:
                if _ref._moId == host_moid:
                    host_ref = _ref
        if not host_ref:
            LOG.debug(_("No valid host is specified."))

        ds_ref = None
        for _ref in cluster_ref.datastore:
            if _ref._moId == ds_moid:
                ds_ref = _ref
        if not ds_ref:
            LOG.error(_LE("No valid datastore is available."))
            raise exception.NoValidDatastore()

        folder_ref = self._get_volume_group_folder(dc_ref, folders)

        return (resource_pool, host_ref, ds_ref, folder_ref)

    def _get_storage_profile_id(self, volume):
        pass

    def _get_extra_config(self, volume):
        return {EXTRA_CONFIG_VOLUME_ID_KEY: volume['uuid'],
                BACKING_UUID_KEY: volume['uuid']}

    def update_backing_disk_uuid(self, backing, disk_uuid):
        """Update backing VM's disk UUID.

        :param backing: Reference to backing VM
        :param disk_uuid: New disk UUID
        """
        LOG.debug("Reconfiguring backing VM: %(backing)s to change disk UUID "
                  "to: %(disk_uuid)s.",
                  {'backing': backing,
                   'disk_uuid': disk_uuid})

        for dev in backing.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk):
                disk_device = dev
                break
        disk_device.backing.uuid = disk_uuid

        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.device = disk_device
        disk_spec.operation = 'edit'

        reconfig_spec = vim.vm.ConfigSpec()
        reconfig_spec.deviceChange = [disk_spec]
        vm_util.reconfigure_vm(backing, reconfig_spec)

        LOG.debug("Backing VM: %(backing)s reconfigured with new disk UUID: "
                  "%(disk_uuid)s.",
                  {'backing': backing,
                   'disk_uuid': disk_uuid})

    def create_volume(self, volume, dc_moid, cluster_moid, ds_moid, host_moid=None, folders=None, create_params=None):
        """Create volume backing under the given host.

        If host is unspecified, any suitable host is selected.

        :param volume: Volume object
        :param host: Reference of the host
        :param create_params: Dictionary specifying optional parameters for
                              backing VM creation
        :return: Reference to the created backing
        """
        # connection_info = {u'driver_volume_type': u'vmdk', 'connector': {'ip': '172.30.126.41', 'initiator': None, 'host': '172.30.126.41', 'instance': 'vm-2547', 'vm_name': 'volume-01'}, 'serial': u'f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'data': {u'name': u'volume-f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'encrypted': False, u'volume': u'vm-2547', u'qos_specs': None, u'volume_id': u'f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'access_mode': u'rw'}}
        #volume = Volume(_name_id=None,admin_metadata={},attach_status='detached',availability_zone='nova',bootable=False,cluster=<?>,cluster_name=None,consistencygroup=<?>,consistencygroup_id=None,created_at=2018-04-03T06:58:03Z,deleted=False,deleted_at=None,display_description='',display_name='v1',ec2_id=None,encryption_key_id=None,glance_metadata=<?>,group=<?>,group_id=None,host='vmdk:172.30.126.41-cinder-volumes@vmdk#vmdk',id=9ea7637c-7e05-4869-99dc-bf64dbbc3ffe,launched_at=None,metadata={},migration_status=None,multiattach=False,previous_status=None,project_id='42710f8b67cb4fc0af85a9a964818a8c',provider_auth=None,provider_geometry=None,provider_id=None,provider_location=None,replication_driver_data=None,replication_extended_status=None,replication_status=None,scheduled_at=2018-04-03T06:58:03Z,size=1,snapshot_id=None,snapshots=<?>,source_volid=None,status='downloading',terminated_at=None,updated_at=2018-04-03T06:58:03Z,user_id='892f46edeec6441db2543d0a9ca0dba5',volume_attachment=<?>,volume_type=VolumeType(9df7d13e-2364-4045-8572-302df1199677),volume_type_id=9df7d13e-2364-4045-8572-302df1199677)
        # create_params = {'temp_backing': True, 'disk_less': True, 'name': '8956c66d-09f2-480d-918e-accc8b3e6672'}

        #volume = {"name": "vol-1", "description": None, "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 1, "multiattach": False, status='creating')

        create_params = create_params or {}

        (resource_pool, host_ref, ds_ref,
                folder_ref) = self._select_ds_for_volume(volume,
                                                         dc_moid,
                                                         cluster_moid,
                                                         ds_moid,
                                                         host_moid=None,
                                                         folders=None)

        # check if a storage profile needs to be associated with the backing VM
        profile_id = self._get_storage_profile_id(volume)

        # Use volume name as the default backing name.
        backing_name = create_params.get(CREATE_PARAM_BACKING_NAME,
                                         volume['name'])

        extra_config = self._get_extra_config(volume)
        # We shoudln't set backing UUID to volume UUID for temporary backing.
        if create_params.get(CREATE_PARAM_TEMP_BACKING):
            del extra_config[BACKING_UUID_KEY]

        # create a backing with single disk
        disk_type = volume.get('disk_type', 'thin')
        size_kb = volume['size'] * units.Mi
        adapter_type = create_params.get(CREATE_PARAM_ADAPTER_TYPE,
                                         'lsiLogic')
        backing = self.create_backing(backing_name,
                                      size_kb,
                                      disk_type,
                                      folder_ref,
                                      resource_pool,
                                      host_ref,
                                      ds_ref.name,
                                      profileId=profile_id,
                                      adapter_type=adapter_type,
                                      extra_config=extra_config)

        self.update_backing_disk_uuid(backing, volume['uuid'])
        return backing

    def attach_disk_to_vm(self, vm_ref, instance,
                          adapter_type, disk_type, vmdk_path=None,
                          disk_size=None, linked_clone=False,
                          device_name=None, disk_io_limits=None):                                                                                                                                                                       
        """Attach disk to VM by reconfiguration."""
        instance_name = vm_ref.name
        (controller_key, unit_number,
         controller_spec) = vm_util.allocate_controller_key_and_unit_number(
                                                              vm_ref,
                                                              adapter_type)

        vmdk_attach_config_spec = vm_util.get_vmdk_attach_config_spec(
                                    disk_type, vmdk_path,
                                    disk_size, linked_clone, controller_key,
                                    unit_number, device_name, disk_io_limits)
        if controller_spec:
            vmdk_attach_config_spec.deviceChange.append(controller_spec)

        LOG.debug("Reconfiguring VM instance %(instance_name)s to attach "
                  "disk %(vmdk_path)s or device %(device_name)s with type "
                  "%(disk_type)s",
                  {'instance_name': instance_name, 'vmdk_path': vmdk_path,
                   'device_name': device_name, 'disk_type': disk_type},
                  instance=instance)

        vm_util.reconfigure_vm(vm_ref, vmdk_attach_config_spec)
        LOG.debug("Reconfigured VM instance %(instance_name)s to attach "
                  "disk %(vmdk_path)s or device %(device_name)s with type "
                  "%(disk_type)s",
                  {'instance_name': instance_name, 'vmdk_path': vmdk_path,
                   'device_name': device_name, 'disk_type': disk_type},
                  instance=instance)

    def _attach_volume_vmdk(self, connection_info, instance,
                            adapter_type=None):
        """Attach vmdk volume storage to VM instance."""
        vm_name = connection_info['connector']['vm_name']
        vm_ref = utils.get_vm_moref(self._content, name=vm_name)
        LOG.debug("_attach_volume_vmdk: %s", connection_info,
                  instance=instance)
        data = connection_info['data']
        volume_ref = utils.get_vm_moref(self._content, moid=data['volume'])

        # Get details required for adding disk device such as
        # adapter_type, disk_type
        vmdk = vm_util.get_vmdk_info(volume_ref)
        adapter_type = adapter_type or vmdk.adapter_type

        # IDE does not support disk hotplug
        if adapter_type == constants.ADAPTER_TYPE_IDE:
            state = vm_ref.runtime.powerState
            if state.lower() != 'poweredoff':
                raise exception.Invalid(_('%s does not support disk '
                                          'hotplug.') % adapter_type)

        # Attach the disk to virtual machine instance
        self.attach_disk_to_vm(vm_ref, instance, adapter_type, vmdk.disk_type,
                               vmdk_path=vmdk.path)

        # Store the uuid of the volume_device
        self._update_volume_details(vm_ref, volume_ref.config.instanceUuid,
                                    vmdk.device.backing.uuid)

        LOG.debug("Attached VMDK: %s", connection_info, instance=instance)

    def _attach_volume_iscsi(self, connection_info, instance,
                             adapter_type=None):
        """Attach iscsi volume storage to VM instance."""
        vm_ref = vm_util.get_vm_ref(self._session, instance)
        # Attach Volume to VM
        LOG.debug("_attach_volume_iscsi: %s", connection_info,
                  instance=instance)

        data = connection_info['data']

        # Discover iSCSI Target
        device_name = self._iscsi_discover_target(data)[0]
        if device_name is None:
            raise exception.StorageError(
                reason=_("Unable to find iSCSI Target"))
        if adapter_type is None:
            # Get the vmdk file name that the VM is pointing to
            hardware_devices = self._session._call_method(
                vutil, "get_object_property", vm_ref, "config.hardware.device")
            adapter_type = vm_util.get_scsi_adapter_type(hardware_devices)

        self.attach_disk_to_vm(vm_ref, instance,
                               adapter_type, 'rdmp',
                               device_name=device_name)
        LOG.debug("Attached ISCSI: %s", connection_info, instance=instance)

    def attach_volume(self, connection_info, instance, adapter_type=None):
        """Attach volume storage to VM instance."""
        driver_type = connection_info['driver_volume_type']
        LOG.debug("Volume attach. Driver type: %s", driver_type,
                  instance=instance)
        if driver_type == DISK_FORMAT_VMDK:
            self._attach_volume_vmdk(connection_info, instance, adapter_type)
#        elif driver_type == DISK_FORMAT_ISCSI:
#            self._attach_volume_iscsi(connection_info, instance, adapter_type)
        else:
            raise exception.VolumeDriverNotFound(driver_type=driver_type)

    def _get_volume_uuid(self, vm_ref, volume_uuid):
        opt_key = "volume-%s" % volume_uuid
        opt_val = None
        for extra_opt in vm_ref.config.extraConfig:
            if extra_opt.key == opt_key:
                opt_val = extra_opt.value
        return opt_val

    def _get_vmdk_backed_disk_device(self, vm_ref, connection_info_data):
        # Get the vmdk file name that the VM is pointing to
        hardware_devices = vm_ref.config.hardware.device

        # Get disk uuid
        disk_uuid = connection_info_data['volume_id']
        device = vm_util.get_vmdk_backed_disk_device(hardware_devices,
                                                     disk_uuid)
        if not device:
            raise exception.DiskNotFound(message=_("Unable to find volume"))
        return device

    def detach_disk_from_vm(self, vm_ref, instance, device,
                            destroy_disk=False):
        """Detach disk from VM by reconfiguration."""
        instance_name = vm_ref.name
        vmdk_detach_config_spec = vm_util.get_vmdk_detach_config_spec(
                                    device, destroy_disk)
        disk_key = device.key
        LOG.debug("Reconfiguring VM instance %(instance_name)s to detach "
                  "disk %(disk_key)s",
                  {'instance_name': instance_name, 'disk_key': disk_key},
                  instance=instance)
        vm_util.reconfigure_vm(vm_ref, vmdk_detach_config_spec)
        LOG.debug("Reconfigured VM instance %(instance_name)s to detach "
                  "disk %(disk_key)s",
                  {'instance_name': instance_name, 'disk_key': disk_key},
                  instance=instance)

    def _get_vmdk_base_volume_device(self, volume_ref):
        # Get the vmdk file name that the VM is pointing to
        hardware_devices = volume_ref.config.hardware.device
        return vm_util.get_vmdk_volume_disk(hardware_devices)

    def _relocate_vmdk_volume(self, volume_ref, res_pool, datastore,
                              host=None):
        """Relocate the volume.

        The move type will be moveAllDiskBackingsAndAllowSharing.
        """
        spec = vm_util.relocate_vm_spec(datastore=datastore,
                                        host=host)
        spec.pool = res_pool
        task = volume_ref.RelocateVM_Task(spec=spec)
        vm_util.wait_for_task(task)

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
#            LOG.warn(_LW("Virtual disk: %s of volume's backing not found."),
#                     original_device_path, exc_info=True)
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
        self.attach_disk_to_vm(volume_ref, instance,
                               adapter_type, disk_type,
                               vmdk_path=current_device_path)

    def _detach_volume_vmdk(self, connection_info, instance):
        """Detach volume storage to VM instance."""
        vm_name = connection_info['connector']['vm_name']
        vm_ref = utils.get_vm_moref(self._content, name=vm_name)
        # Detach Volume from VM
        LOG.debug("_detach_volume_vmdk: %s", connection_info,
                  instance=instance)
        data = connection_info['data']
        volume_ref = utils.get_vm_moref(self._content, moid=data['volume'])

        device = self._get_vmdk_backed_disk_device(vm_ref, data)

        # Get details required for adding disk device such as
        # adapter_type, disk_type
        vmdk = vm_util.get_vmdk_info(volume_ref)

        # IDE does not support disk hotplug
        if vmdk.adapter_type == constants.ADAPTER_TYPE_IDE:
            state = vm_ref.runtime.powerState
            if state.lower() != 'poweredoff':
                raise exception.Invalid(_('%s does not support disk '
                                          'hotplug.') % vmdk.adapter_type)

        self._consolidate_vmdk_volume(instance, vm_ref, device, volume_ref,
                                      adapter_type=vmdk.adapter_type,
                                      disk_type=vmdk.disk_type)

        self.detach_disk_from_vm(vm_ref, instance, device)
                                                                                                                                                                   
        # Remove key-value pair <volume_id, vmdk_uuid> from instance's
        # extra config. Setting value to empty string will remove the key.
        self._update_volume_details(vm_ref, data['volume_id'], "")

        LOG.debug("Detached VMDK: %s", connection_info, instance=instance)

    def _detach_volume_iscsi(self, connection_info, instance):
        """Detach volume storage to VM instance."""
        vm_ref = vm_util.get_vm_ref(self._session, instance)
        # Detach Volume from VM
        LOG.debug("_detach_volume_iscsi: %s", connection_info,
                  instance=instance)
        data = connection_info['data']

        # Discover iSCSI Target
        device_name, uuid = self._iscsi_get_target(data)
        if device_name is None:
            raise exception.StorageError(
                reason=_("Unable to find iSCSI Target"))

        # Get the vmdk file name that the VM is pointing to
        hardware_devices = self._session._call_method(vutil,
                                                      "get_object_property",
                                                      vm_ref,
                                                      "config.hardware.device")
        device = vm_util.get_rdm_disk(hardware_devices, uuid)
        if device is None:
            raise exception.DiskNotFound(message=_("Unable to find volume"))
        self.detach_disk_from_vm(vm_ref, instance, device, destroy_disk=True)
        LOG.debug("Detached ISCSI: %s", connection_info, instance=instance)

    def detach_volume(self, connection_info, instance):
        """Detach volume storage to VM instance."""
        driver_type = connection_info['driver_volume_type']
        LOG.debug("Volume detach. Driver type: %s", driver_type,
                  instance=instance)
        if driver_type == constants.DISK_FORMAT_VMDK:
            self._detach_volume_vmdk(connection_info, instance)
#        elif driver_type == constants.DISK_FORMAT_ISCSI:
#            self._detach_volume_iscsi(connection_info, instance)
        else:
            raise exception.VolumeDriverNotFound(driver_type=driver_type)


    def _update_volume_details(self, vm_ref, volume_uuid, device_uuid):
        # Store the uuid of the volume_device
        volume_option = 'volume-%s' % volume_uuid
        extra_opts = {volume_option: device_uuid}

        extra_config_specs = vm_util.get_vm_extra_config_spec(extra_opts)
        vm_util.reconfigure_vm(vm_ref, extra_config_specs)



if __name__ ==  '__main__':
    service_instance=connect.SmartConnect(host="172.30.126.41", user="administrator@vsphere.local", pwd="Teamsun@1")
    content=service_instance.RetrieveContent()

    vol_opt = VMwareVolumeOps(content)
    name = 'volume-001'
    size_kb = 10 * 1024 * 1024
    disk_type = 'thin'

    datacenters = content.viewManager.CreateContainerView(content.rootFolder,[vim.Datacenter], True).view
    datacenter = datacenters[0]
    folder = datacenter.vmFolder
    resource_pool = datacenter.hostFolder.childEntity[0].resourcePool
    host = None
    ds_name = datacenter.datastore[0].name

    #print vol_opt.create_backing(name, size_kb, disk_type, folder, resource_pool,
    #                             host, ds_name, profileId=None, adapter_type='lsiLogicsas',
    #                             extra_config=None)
    volume1 = {"name": "vol-1", "description": None, "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 1, "disk_type": "thin", "multiattach": False, "status": "creating"} # vm-2663
    volume2 = {"name": "vol-2", "description": None, "uuid": "5a60951d-6652-4c85-bad3-4350de7d308a", "size": 1, "disk_type": "thin", "multiattach": False, "status": "creating"} # vm-2664
    dc_moid = 'datacenter-2'
    cluster_moid = 'domain-c14'
    ds_moid = 'datastore-1415'
    volume = volume2
    #print vol_opt.create_volume(volume, dc_moid, cluster_moid, ds_moid, host_moid=None, create_params=None)


    # connection_info: {u'driver_volume_type': u'vmdk', 'connector': {'ip': '172.30.126.41', 'initiator': None, 'host': '172.30.126.41', 'instance': vm-2504}, 'serial': u'f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'data': {u'name': u'volume-f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'encrypted': False, u'volume': u'vm-2507', u'qos_specs': None, u'volume_id': u'f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'access_mode': u'rw'}}
    connection_info = {u'driver_volume_type': u'vmdk', 'connector': {'ip': '172.30.126.41', 'initiator': None, 'host': '172.30.126.41', 'instance': 'vm-2663', 'vm_name': 'vol-1'}, 'serial': u'f0e6fa4e-1fcc-481c-aaf9-3a2dfdd4488f', u'data': {u'name': u'vol-1', u'encrypted': False, u'volume': u'vm-2664', u'qos_specs': None, u'volume_id': u'5a60951d-6652-4c85-bad3-4350de7d308a', u'access_mode': u'rw'}}
    #vol_opt.attach_volume(connection_info, None)
    vol_opt.detach_volume(connection_info, None)
