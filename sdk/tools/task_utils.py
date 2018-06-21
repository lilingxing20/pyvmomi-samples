# -*- coding:utf-8 -*-

from __future__ import absolute_import

from pyVmomi import vmodl

import logging

LOG = logging.getLogger(__name__)


def reconfig_vm_task(vm_moref, config_spec):
    try:
        task_moref = vm_moref.ReconfigVM_Task(spec=config_spec)
    except vmodl.MethodFault as error:
        LOG.exception("Caught vmodl fault : " + error.msg)
    return task_moref
