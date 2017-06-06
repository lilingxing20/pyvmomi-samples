# -*- coding:utf-8 -*-

"""
@@ function:
@ datastore_info_json: get datastote details
@ storage_pod_info_json: get storage pod details

"""


from pyVmomi import vim


def datastore_info_json(ds_obj):
    """
    To json information for a particular datastore
    @ ds_obj: vim.DataStore
    """
    ds_details = {}
    ds_details['name'] = ds_obj.name
    ds_details['tag'] = ds_obj.tag
    ds_details['capacity'] = ds_obj.summary.capacity
    ds_details['freeSpace'] = ds_obj.summary.freeSpace
    ds_details['url'] = ds_obj.summary.url
    ds_details['accessible'] = ds_obj.summary.accessible
    ds_details['multipleHostAccess'] = ds_obj.summary.multipleHostAccess
    ds_details['type'] = ds_obj.summary.type
    ds_details['ssd'] = ds_obj.info.vmfs.ssd
    ds_details['local'] = ds_obj.info.vmfs.local
    return ds_details


def storage_pod_info_json(pod_obj):
    """
    To json information for a particular storage pod
    @ pod_obj: vim.StoragePod
    """
    pod_details = {}

    return pod_details
