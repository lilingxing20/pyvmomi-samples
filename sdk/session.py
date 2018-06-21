# -*- coding:utf-8 -*-

from __future__ import absolute_import

import atexit
import logging
import ssl
from builtins import object

from pyVim import connect
from pyVmomi import vim
# from pyVmomi import vmodl


LOG = logging.getLogger(__name__)


class VcenterInfo(object):
    def __init__(self, host, user, pwd, port=443):
        self.host = host
        self.user = user
        self.pwd = pwd
        self.port = port


class VcenterSession(object):
    """
    Sets up a session with the VC/ESX host and handles all
      the calls made to the host.
    """
    def __init__(self, vcenter_info):
        self.host = vcenter_info.host
        self.user = vcenter_info.user
        self.pwd = vcenter_info.pwd
        self.port = vcenter_info.port
        # connect vcenter server
        self.si = self.auth_vcenter()

    def auth_vcenter(self):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            service_instance = connect.SmartConnect(host=self.host,
                                                    user=self.user,
                                                    pwd=self.pwd,
                                                    port=int(self.port),
                                                    sslContext=context)
            atexit.register(connect.Disconnect, service_instance)

            LOG.info("The vCenter has authenticated.")
            LOG.debug("The vCenter server is {}!".format(self.host))
            # NOTE (hartsock): only a successfully authenticated session has a
            # session key aka session id.
            session_id = service_instance.content.sessionManager.currentSession.key
            LOG.debug("current session id: {}".format(session_id))

            return service_instance

        except vim.fault.InvalidLogin as error:
            LOG.exception("Caught vmodl fault : " + error.msg)
        # except vmodl.MethodFault as error:
        #     LOG.exception("Caught vmodl fault : " + error.msg)
        except Exception as error:
            LOG.exception(error)

    def get_session_id(self):
        if self.si and self.si.content.sessionManager.currentSession:
            return self.si.content.sessionManager.currentSession.key
        else:
            return None

    def disconnect(self):
        if self.si:
            connect.Disconnect(self.si)

    def is_connected(self):
        if self.si and self.si.content.sessionManager.currentSession:
            return True
        else:
            return False


class VcenterSessionManager(object):
    _session_cache = dict()

    def __init__(self):
        pass

    def get_vcenter_session(self, vcenter_info):
        _host_port = "%s_%s" % (vcenter_info.host, vcenter_info.port)
        session = self._session_cache.get(_host_port)
        if not session:
            session = VcenterSession(vcenter_info)
            self._session_cache[_host_port] = session
            LOG.debug("init service instance: %s" % session.get_session_id())
        else:
            if not session.is_connected():
                LOG.debug('get service instance from cache, but it is timeout')
                session = VcenterSession(vcenter_info)
                self._session_cache[_host_port] = session
                LOG.debug("init new service instance: %s" % session.get_session_id())
            else:
                LOG.debug("get service instance from cache: %s" % session.get_session_id())
        return session

    def clear(self, vcenter_info):
        _host_port = "%s_%s" % (vcenter_info.host, vcenter_info.port)
        if _host_port in self._session_cache.keys():
            self._session_cache[_host_port].disconnect()
            del self._session_cache[_host_port]
