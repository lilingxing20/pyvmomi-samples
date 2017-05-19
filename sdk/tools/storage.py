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
    @ ds_obj: vim.Datastore
    """
    ds_details = {}

    return ds_details


def storage_pod_info_json(pod_obj):
    """
    To json information for a particular storage pod
    @ pod_obj: vim.StoragePod
    """
    pod_details = {}

    return pod_details
