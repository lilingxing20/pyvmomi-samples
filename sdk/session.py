# -*- coding:utf-8 -*-

import atexit
import ssl

from pyVim import connect
from pyVmomi import vmodl


import logging
LOG = logging.getLogger(__name__)


class VMwareSession(object):
    """
    Sets up a session with the VC/ESX host and handles all
      the calls made to the host.
    """
    def __init__(self, host, user, pwd, port=443):
        self.host = host
        self.user = user
        self.pwd = pwd
        self.port = port
        self.si = None

        self.auth_vcenter()

#    def __del__(self):
#        if self.si:
#            connect.Disconnect(self.si)

    def auth_vcenter(self):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            service_instance = connect.SmartConnect(host=self.host,
                                                    user=self.user,
                                                    pwd=self.pwd,
                                                    port=int(self.port),
                                                    sslContext=context)
            if not service_instance:
                LOG.error("Could not connect to the specified host using "
                          "specified username and password")
            else:
                self.si = service_instance

            atexit.register(connect.Disconnect, self.si)

            LOG.info("The vCenter has authenticated.")
            LOG.debug("The vCenter server is {}!".format(self.host))
            # NOTE (hartsock): only a successfully authenticated session has a
            # session key aka session id.
            session_id = service_instance.content.sessionManager.currentSession.key
            LOG.debug("current session id: {}".format(session_id))

        except vmodl.MethodFault as error:
            LOG.exception("Caught vmodl fault : " + error.msg)

    def is_connected(self):
        if self.si:
            return True
        else:
            return False
