# -*- coding:utf-8 -*-

"""
Trying to connect to vCenter, verify the user password.

@ host: vCenter host ip
@ user: vCenter username
@ pwd:  vCenter passowrd
"""

import atexit
import logging

from pyVim import connect
from pyVmomi import vmodl

LOG = logging.getLogger(__name__)


def auth_vcenter(host, user, pwd, port=443):

    try:
        service_instance = connect.SmartConnect(host=host,
                                                user=user,
                                                pwd=pwd,
                                                port=int(port))

        atexit.register(connect.Disconnect, service_instance)

        LOG.info("The vCenter has authenticated.")
        LOG.debug("The vCenter server is {}!".format(host))
        # NOTE (hartsock): only a successfully authenticated session has a
        # session key aka session id.
        session_id = service_instance.content.sessionManager.currentSession.key
        LOG.debug("current session id: {}".format(session_id))

    except vmodl.MethodFault as error:
        LOG.exception("Caught vmodl fault : " + error.msg)
        return -1

    return 0
