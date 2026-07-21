"""
Command line entrypoints for koan and cobbler-register.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import argparse
import os
import sys
import traceback

from koan import __version__

from . import utils
from .app import Koan
from .cexceptions import InfoException
from .register import Register


def main():
    """
    Command line stuff...
    """

    try:
        utils.setupLogging("koan")
    except:
        # most likely running RHEL3, where we don't need virt logging anyway
        pass

    p = argparse.ArgumentParser()
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__ or 'unknown'}",
    )
    p.add_argument(
        "-k", "--kopts", dest="kopts_override", help="append additional kernel options"
    )
    p.add_argument(
        "-l",
        "--list",
        dest="list_items",
        help="lists remote items (EX: profiles, systems, or images)",
    )
    p.add_argument(
        "-v",
        "--virt",
        dest="is_virt",
        action="store_true",
        default=None,
        help="install new virtual guest",
    )
    p.add_argument(
        "-u",
        "--update-files",
        dest="is_update_files",
        action="store_true",
        default=None,
        help="update templated files from cobbler config management",
    )
    p.add_argument(
        "-c",
        "--update-config",
        dest="is_update_config",
        action="store_true",
        default=None,
        help="update system configuration from cobbler config management",
    )
    p.add_argument(
        "--summary",
        dest="summary",
        action="store_true",
        default=None,
        help="print configuration run stats",
    )
    p.add_argument(
        "-V",
        "--virt-name",
        dest="virt_name",
        help="use this name for the virtual guest",
    )
    p.add_argument(
        "-r",
        "--replace-self",
        dest="is_replace",
        action="store_true",
        default=None,
        help="reinstall this host at next reboot",
    )
    p.add_argument(
        "-D",
        "--display",
        dest="is_display",
        action="store_true",
        default=None,
        help="display the configuration stored in cobbler for the given object",
    )
    p.add_argument("-p", "--profile", dest="profile", help="use this cobbler profile")
    p.add_argument("-y", "--system", dest="system", help="use this cobbler system")
    p.add_argument("-i", "--image", dest="image", help="use this cobbler image")
    p.add_argument(
        "-s",
        "--server",
        dest="server",
        default=os.environ.get("COBBLER_SERVER", ""),
        help="attach to this cobbler server",
    )
    p.add_argument(
        "-S",
        "--static-interface",
        dest="static_interface",
        help="use static network configuration from this interface while installing",
    )
    p.add_argument("-t", "--port", dest="port", help="cobbler port (default 80)")
    p.add_argument(
        "-w",
        "--vm-poll",
        dest="should_poll",
        action="store_true",
        default=None,
        help="for xen/qemu/KVM, poll & restart the VM after the install is done",
    )
    p.add_argument(
        "-P", "--virt-path", dest="virt_path", help="override virt install location"
    )
    p.add_argument(
        "--force-path",
        dest="force_path",
        action="store_true",
        default=None,
        help="Force overwrite of virt install location",
    )
    p.add_argument(
        "-T", "--virt-type", dest="virt_type", help="override virt install type"
    )
    p.add_argument(
        "-B", "--virt-bridge", dest="virt_bridge", help="override virt bridge"
    )
    p.add_argument(
        "-n",
        "--nogfx",
        action="store_true",
        dest="no_gfx",
        default=None,
        help="disable Xen graphics (xenpv,xenfv)",
    )
    p.add_argument(
        "-g",
        "--graphics",
        dest="gfx_type",
        default="vnc",
        help="specify the graphics type: vnc, sdl, spice, none",
    )
    p.add_argument(
        "--virt-auto-boot",
        action="store_true",
        dest="virt_auto_boot",
        default=None,
        help="set VM for autoboot",
    )
    p.add_argument(
        "--virt-pxe-boot",
        action="store_true",
        dest="virt_pxe_boot",
        default=None,
        help="PXE boot for installation override",
    )
    p.add_argument(
        "--add-reinstall-entry",
        dest="add_reinstall_entry",
        action="store_true",
        default=None,
        help="when used with --replace-self, just add entry to grub, \
        do not make it the default",
    )
    p.add_argument(
        "-C",
        "--livecd",
        dest="live_cd",
        action="store_true",
        default=None,
        help="used by the custom livecd only, not for humans",
    )
    p.add_argument(
        "--kexec",
        dest="use_kexec",
        action="store_true",
        default=None,
        help="Instead of writing a new bootloader config when using --replace-self, just kexec the new kernel and "
        "initrd ",
    )
    p.add_argument(
        "--no-copy-default",
        dest="no_copy_default",
        action="store_true",
        default=None,
        help="Do not copy the kernel args from the default kernel entry when using --replace-self",
    )
    p.add_argument(
        "--embed",
        dest="embed_autoinst",
        action="store_true",
        default=None,
        help="When used with  --replace-self, embed the autoinst in the initrd to overcome potential DHCP timeout "
        "issues. (seldom needed) ",
    )
    p.add_argument(
        "--qemu-disk-type",
        dest="qemu_disk_type",
        help="when used with --virt_type=qemu, add select of disk driver types: ide,scsi,virtio",
    )
    p.add_argument(
        "--qemu-net-type",
        dest="qemu_net_type",
        help="when used with --virt_type=qemu, select type of network device to use: e1000, ne2k_pci, pcnet, rtl8139, "
        "virtio ",
    )
    p.add_argument(
        "--qemu-machine-type",
        dest="qemu_machine_type",
        help="when used with --virt_type=qemu, select type of machine type to emulate: pc, pc-1.0, pc-0.15",
    )
    p.add_argument(
        "--wait",
        # default to 0 for koan backwards compatibility
        dest="wait",
        type=int,
        default=0,
        help="pass the --wait=<INT> argument to virt-install",
    )
    p.add_argument(
        "--noreboot",
        # default to False for koan backwards compatibility
        dest="noreboot",
        default=False,
        action="store_true",
        help="pass the --noreboot argument to virt-install",
    )
    p.add_argument(
        "--import",
        # default to False for koan backwards compatibility
        dest="osimport",
        default=False,
        action="store_true",
        help="pass the --import argument to virt-install",
    )

    options = p.parse_args()

    try:
        k = Koan()
        k.list_items = options.list_items
        k.server = options.server
        k.is_virt = options.is_virt
        k.is_update_files = options.is_update_files
        k.is_update_config = options.is_update_config
        k.summary = options.summary
        k.is_replace = options.is_replace
        k.is_display = options.is_display
        k.profile = options.profile
        k.system = options.system
        k.image = options.image
        k.live_cd = options.live_cd
        k.virt_path = options.virt_path
        k.force_path = options.force_path
        k.virt_type = options.virt_type
        k.virt_bridge = options.virt_bridge
        k.add_reinstall_entry = options.add_reinstall_entry
        k.kopts_override = options.kopts_override
        k.static_interface = options.static_interface
        k.use_kexec = options.use_kexec
        k.no_copy_default = options.no_copy_default
        k.should_poll = options.should_poll
        k.embed_autoinst = options.embed_autoinst
        k.virt_auto_boot = options.virt_auto_boot
        k.virt_pxe_boot = options.virt_pxe_boot
        k.qemu_disk_type = options.qemu_disk_type
        k.qemu_net_type = options.qemu_net_type
        k.qemu_machine_type = options.qemu_machine_type
        k.virtinstall_wait = options.wait
        k.virtinstall_noreboot = options.noreboot
        k.virtinstall_osimport = options.osimport

        if options.virt_name is not None:
            k.virt_name = options.virt_name
        if options.port is not None:
            k.port = options.port
        if options.gfx_type is not None and options.no_gfx is not None:
            raise InfoException(
                "Error: cannot specify both -n|--no_gfx and -g|--graphics"
            )
        if options.gfx_type == "none" or options.no_gfx is not None:
            k.gfx_type = None
        else:
            k.gfx_type = options.gfx_type
        k.run()

    except Exception as e:
        xa, xb, tb = sys.exc_info()
        try:
            getattr(e, "from_koan")
            print(str(e)[1:-1])  # nice exception, no traceback needed
        except:
            print(xa)
            print(xb)
            print("".join(traceback.format_list(traceback.extract_tb(tb))))
        return 1

    return 0


def register_main():
    """
    Command line stuff...
    """

    p = argparse.ArgumentParser()
    p.add_argument(
        "-s",
        "--server",
        dest="server",
        default=os.environ.get("COBBLER_SERVER", ""),
        help="attach to this cobbler server",
    )
    p.add_argument(
        "-f",
        "--fqdn",
        dest="hostname",
        default="",
        help="override the discovered hostname",
    )
    p.add_argument(
        "-p", "--port", dest="port", default="80", help="cobbler port (default 80)"
    )
    p.add_argument(
        "-P",
        "--profile",
        dest="profile",
        default="",
        help="assign this profile to this system",
    )
    p.add_argument(
        "-b",
        "--batch",
        dest="batch",
        action="store_true",
        default=None,
        help="indicates this is being run from a script",
    )

    options = p.parse_args()
    # if not os.getuid() == 0:
    #    print("koan requires root access")
    #    return 3

    try:
        k = Register()
        k.server = options.server
        k.port = options.port
        k.profile = options.profile
        k.hostname = options.hostname
        k.batch = options.batch
        k.run()
    except Exception as e:
        xa, xb, tb = sys.exc_info()
        try:
            getattr(e, "from_koan")
            print(str(e)[1:-1])  # nice exception, no traceback needed
        except:
            print(xa)
            print(xb)
            print("".join(traceback.format_list(traceback.extract_tb(tb))))
        return 1

    return 0
