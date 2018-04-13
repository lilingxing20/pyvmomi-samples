#!/usr/bin/env python
# -*- coding:utf-8 -*-

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
import utils

import spec_util
import task_util


LOG = logging.getLogger(__name__)


class VMwareVolumeOps(object):
    """Manages volume operations. """

    def __init__(self, content, max_objects=100):
        self._content = content
        self._max_objects = max_objects
        self._folder_cache = {}

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
        folder_names = ['Volumes'] + folders

        vmfolder = dc_ref.vmFolder
        f_ref = None
        for folder_name in folder_names:
            f_ref = utils.get_child_ref_by_name(vmfolder, folder_name, vim.Folder)
            if f_ref:
                vmfolder = f_ref
            else:
                vmfolder = task_util.create_inventory_folder(vmfolder, folder_name)
        return vmfolder

    def _get_storage_profile_id(self, volume):
        pass

    def _select_ds_for_volume(self, dc_moid, cluster_moid, ds_moid,
                              host_moid=None, folders=None):
        """Select datastore that can accommodate the given volume's backing.

        Returns the selected datastore summary along with a compute host and
        its resource pool and folder where the volume can be created
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

        folder_ref = self._get_volume_group_folder(dc_ref, folders)

        return (resource_pool, host_ref, ds_ref, folder_ref)

    def create_volume(self, volume, dc_moid, cluster_moid, ds_moid,
                      host_moid=None, folders=None):
        """Create volume backing under the given host.

        If host is unspecified, any suitable host is selected.

        :param volume: Volume object
        :param host: Reference of the host
        :return: Reference to the created backing
        """
        # volume = {"name": "vol-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 1}
        # volume = {"name": "vol-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe", "size": 1,
        #           "disk_type": "thin", "adapter_type": "lsiLogicsas",
        #           "hw_version": "vmx-11", "description": "This is volume"}

        (resource_pool, host_ref, ds_ref,
                folder_ref) = self._select_ds_for_volume(dc_moid,
                                                         cluster_moid,
                                                         ds_moid,
                                                         host_moid,
                                                         folders)

        # check if a storage profile needs to be associated with the backing VM
        profile_id = self._get_storage_profile_id(volume)

        # Use volume name as the default display name.
        display_name = volume['name']
        uuid = volume['uuid']
        description = volume.get('description')
        hw_version = volume.get('hw_version')
        disk_type = volume.get('disk_type', 'thin')
        size_kb = volume['size'] * units.Mi
        adapter_type = volume.get('adapter_type', 'lsiLogic')
        create_spec = spec_util.create_volume_config_spec(display_name,
                                                          uuid,
                                                          ds_ref.name,
                                                          size_kb,
                                                          disk_type,
                                                          adapter_type,
                                                          hw_version=hw_version,
                                                          profile_id=profile_id,
                                                          description=description)
        volume_ref = task_util.create_vm_task(folder_ref, resource_pool,
                                              host_ref, create_spec)
        return volume_ref

    def destroy_volume(self, volume):
        """Delete volume
        """
        # volume = {"name": "vol-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe"}
        volume_ref = utils.get_vm_moref(self._content, name=volume['name'],
                                        uuid=volume['uuid'])
        (status, info) = (-1, None)
        if volume_ref:
            (status, info) = task_util.destroy_vm_task(volume_ref)
        return status

