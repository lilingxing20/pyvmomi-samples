from pyVim import connect
from pyVmomi import vim

from volumeopt import VMwareVolumeOps
from vmopt import VMwareVmOps


if __name__ ==  '__main__':
    service_instance=connect.SmartConnect(host="172.30.126.41", user="administrator@vsphere.local", pwd="Teamsun@1")
    content=service_instance.RetrieveContent()

    volume_opt = VMwareVolumeOps(content)

    volume = {"name": "vol-1", "uuid": "5ae09832-45d4-4e90-a4e7-76f2de891168",
               "size": 1, "disk_type": "thin", "adapter_type": "lsiLogicsas",
              "hw_version": "vmx-11", "description": "This is volume"}
    dc_moid = 'datacenter-2'
    cluster_moid = 'domain-c14'
    ds_moid = 'datastore-1416'
    host_moid = 'host-682'
    folders=['test']
#    volume_ref = volume_opt.create_volume(volume, dc_moid, cluster_moid, ds_moid, host_moid, folders)
#    print volume_ref

#    volume = {"name": "vol-1", "uuid": "5ae09832-45d4-4e90-a4e7-76f2de891168"}
#    status = volume_opt.destroy_volume(volume)
#    print status

    vm_opt = VMwareVmOps(content)
    instance = {"name": "vm-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe",
                "memory_mb": 1024, "vcpus": 2, "cores_per_socket": 1,
                "vif_infos": [{'network_name': 'VM127', 'network_type': 'Network', 'dvpg_moid': 'network-530', 'vif_model': 'vmxnet3', 'mac_address': '00:50:56:ab:18:02',  'iface_id': 1}],
                "size": 10, "disk_type": "thin", "adapter_type": "lsiLogicsas",
                "hw_version": "vmx-11", "description": "This is vm"}

    vm_ref = vm_opt.create_vm(instance, dc_moid, cluster_moid, ds_moid, host_moid, folders)
    print vm_ref

#    instance = {"name": "vol-1", "uuid": "9ea7637c-7e05-4869-99dc-bf64dbbc3ffe"}
#    status = vm_opt.destroy_vm(instance)
#    print status

#    instance = {'name': 'vol-1', 'moid': 'vm-2747'}
#    volume = {"name": "vol-1", 'moid': 'vm-2746'}
#    vm_opt.attach_volume('vmdk', instance, volume)
#    instance = {'name': 'vol-1', 'moid': 'vm-2747'}
#    volume = {"name": "vol-1", 'moid': 'vm-2746'}
#    vm_opt.detach_volume('vmdk', instance, volume)




