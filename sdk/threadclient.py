# -*- coding:utf-8 -*-

import logging
import multiprocessing
import Queue
import sys
import threading

import client

LOG = logging.getLogger(__name__)

tasks_queue = Queue.Queue(0)


def put_task_in_queue(task_list):
    global tasks_queue
    for t in task_list:
        tasks_queue.put(t)


def create_task_clone_vm(vmlist):
    """
    """
    put_task_in_queue(vmlist)
    thread_task = myThread(mult_process_clone_vm)
    # thread_task.setDaemon(True)
    thread_task.start()
    return vmlist


def mult_process_clone_vm(processes=4):
    """
    """
    global tasks_queue
    process_pool = multiprocessing.Pool(processes=processes)
    result = []
    while True:
        if tasks_queue.empty():
            break
        vmdict = tasks_queue.get()
        result.append(process_pool.apply_async(run_clone_vm, (vmdict, )))
    process_pool.close()
    process_pool.join()

    for res in result:
        ret = res.get()
        LOG.debug(ret)


def run_clone_vm(vmdict):
    """
    """
    vc_auth = vmdict.get('vc_auth')
    host = vc_auth.get('host')
    user = vc_auth.get('user')
    pwd = vc_auth.get('pwd')
    vc = client.VMwareClient(host, user, pwd)
    if not vc.is_connected():
        return {"status": -1, "msg": "Connect vcenter server failed"}

    template_name = vmdict.get('template_name')
    vm_name = vmdict.get('name')
    datacenter_name = vmdict.get('datacenter_name')
    cluster_name = vmdict.get('cluster_name')
    res_pool_name = vmdict.get('res_pool_name')
    datastore_name = vmdict.get('datastore_name')
    datastore_cluster = vmdict.get('datastore_cluster')
    vmfolder_name = vmdict.get('vmfolder_name')
    cpunum = vmdict.get('cpunum')
    corenum = vmdict.get('corenum')
    memoryMB = vmdict.get('memoryMB')
    poweron = vmdict.get('poweron')
    vm_net = vmdict.get('net')
    dnslist = vmdict.get('dnslist')
    domain = vmdict.get('domain')
    hostname = vmdict.get('hostname')
    disktype = vmdict.get('disktype')
    disksize = vmdict.get('disksize')

    (ret_status, msg) = (0, "VM %s is cloned" % vm_name)
    try:
        ret_status = vc.clone_vm(template_name, vm_name,
                                 datacenter_name, cluster_name,
                                 res_pool_name, datastore_cluster,
                                 datastore_name, vmfolder_name,
                                 disktype, disksize, cpunum, corenum,
                                 memoryMB, poweron, vm_net,
                                 dnslist, domain, hostname)
    except Exception, e:
        msg = "Caught clone vm fault : %s" % e
    return {"status": ret_status, "msg": msg}


class myThread(threading.Thread):
    def __init__(self, call_back):
        threading.Thread.__init__(self)
        self.call_back = call_back

    def run(self):
        try:
            self.call_back()
        except Exception, e:
            print e
#            LOG.exception("Caught myThread call_back func fault : %s" % e)
