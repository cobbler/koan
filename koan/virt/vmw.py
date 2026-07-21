"""
Virtualization installation functions.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os
import subprocess
from typing import Any, Dict, List, Optional, Union, cast

from koan.cexceptions import InfoException, VirtCreateException

IMAGE_DIR = "/var/lib/vmware/images"
VMX_DIR = "/var/lib/vmware/vmx"

# FIXME: what to put for guestOS
# FIXME: are other settings ok?
TEMPLATE = """
#!/usr/bin/vmware
config.version = "8"
virtualHW.version = "4"
numvcpus = "2"
scsi0.present = "TRUE"
scsi0.virtualDev = "lsilogic"
scsi0:0.present = "TRUE"
scsi0:0.writeThrough = "TRUE"
ide1:0.present = "TRUE"
ide1:0.deviceType = "cdrom-image"
Ethernet0.present = "TRUE"
Ethernet0.AddressType = "static"
Ethernet0.Address = "%(MAC_ADDRESS)s"
Ethernet0.virtualDev = "e1000"
guestOS = "linux"
priority.grabbed = "normal"
priority.ungrabbed = "normal"
powerType.powerOff = "hard"
powerType.powerOn = "hard"
powerType.suspend = "hard"
powerType.reset = "hard"
floppy0.present = "FALSE"
scsi0:0.filename = "%(VMDK_IMAGE)s"
displayName = "%(IMAGE_NAME)s"
memsize = "%(MEMORY)s"
"""
# ide1:0.filename = "%(PATH_TO_ISO)s"


def make_disk(disksize: Union[int, str], image: str) -> None:
    cmd = [
        "vmware-vdiskmanager",
        "-c",
        "-a",
        "lsilogic",
        "-s",
        "%sGb" % disksize,
        "-t",
        "0",
        image,
    ]
    print("- %s" % cmd)
    rc = subprocess.call(cmd)
    if rc != 0:
        raise VirtCreateException("command failed")


def make_vmx(
    path: str,
    vmdk_image: str,
    image_name: str,
    mac_address: str,
    memory: Union[int, str],
) -> None:
    template_params = {
        "VMDK_IMAGE": vmdk_image,
        "IMAGE_NAME": image_name,
        "MAC_ADDRESS": mac_address.lower(),
        "MEMORY": memory,
    }
    templated = TEMPLATE % template_params
    fd = open(path, "w+")
    fd.write(templated)
    fd.close()


def register_vmx(vmx_file: str) -> None:
    cmd = ["vmware-cmd", "-s", "register", vmx_file]
    print("- %s" % cmd)
    rc = subprocess.call(cmd)
    if rc != 0:
        raise VirtCreateException("vmware registration failed")


def start_vm(vmx_file: str) -> None:
    os.chmod(vmx_file, 0o755)
    cmd = ["vmware-cmd", vmx_file, "start"]
    print("- %s" % cmd)
    rc = subprocess.call(cmd)
    if rc != 0:
        raise VirtCreateException("vm start failed")


def start_install(
    name: Optional[str] = None,
    ram: Optional[Union[int, str]] = None,
    disks: Optional[List[Any]] = None,
    mac: Optional[str] = None,
    uuid: Optional[str] = None,
    extra: Optional[str] = None,
    vcpus: Optional[int] = None,
    profile_data: Optional[Dict[str, Any]] = None,
    arch: Optional[str] = None,
    gfx_type: Optional[str] = None,
    fullvirt: Optional[bool] = True,
    bridge: Optional[str] = None,
    virt_type: Optional[str] = None,
    virt_auto_boot: bool = False,
    qemu_driver_type: Optional[str] = None,
    qemu_net_type: Optional[str] = None,
) -> Optional[int]:
    profile_data = cast(Dict[str, Any], profile_data)

    if "file" in profile_data:
        raise InfoException("vmware does not work with --image yet")

    mac = None
    if "interfaces" not in profile_data:
        print("- vmware installation requires a system, not a profile")
        return 1
    for iname in profile_data["interfaces"]:
        intf = profile_data["interfaces"][iname]
        mac = intf["mac_address"]
    if mac is None:
        print("- no MAC information available in this record, cannot install")
        return 1

    print("DEBUG: name=%s" % name)
    print("DEBUG: ram=%s" % ram)
    print("DEBUG: mac=%s" % mac)
    print("DEBUG: disks=%s" % disks)
    # starts vmware using PXE.  disk/mem info come from Cobbler
    # rest of the data comes from PXE which is also intended
    # to be managed by Cobbler.

    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    if not os.path.exists(VMX_DIR):
        os.makedirs(VMX_DIR)

    disks = cast(List[Any], disks)
    if len(disks) != 1:
        raise VirtCreateException("vmware support is limited to 1 virtual disk")

    disksize = disks[0][1]

    image = "%s/%s" % (IMAGE_DIR, name)
    print("- saving virt disk image as %s" % image)
    make_disk(disksize, image)
    vmx = "%s/%s" % (VMX_DIR, name)
    print("- saving vmx file as %s" % vmx)
    make_vmx(vmx, image, cast(str, name), mac, cast(Union[int, str], ram))
    register_vmx(vmx)
    start_vm(vmx)
