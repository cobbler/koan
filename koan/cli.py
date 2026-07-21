"""
Command line entrypoints for koan and cobbler-register.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os
import sys
import traceback
from optparse import OptionParser

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

    p = OptionParser()
    p.add_option(
        "-k", "--kopts", dest="kopts_override", help="append additional kernel options"
    )
    p.add_option(
        "-l",
        "--list",
        dest="list_items",
        help="lists remote items (EX: profiles, systems, or images)",
    )
    p.add_option(
        "-v",
        "--virt",
        dest="is_virt",
        action="store_true",
        help="install new virtual guest",
    )
    p.add_option(
        "-u",
        "--update-files",
        dest="is_update_files",
        action="store_true",
        help="update templated files from cobbler config management",
    )
    p.add_option(
        "-c",
        "--update-config",
        dest="is_update_config",
        action="store_true",
        help="update system configuration from cobbler config management",
    )
    p.add_option(
        "",
        "--summary",
        dest="summary",
        action="store_true",
        help="print configuration run stats",
    )
    p.add_option(
        "-V",
        "--virt-name",
        dest="virt_name",
        help="use this name for the virtual guest",
    )
    p.add_option(
        "-r",
        "--replace-self",
        dest="is_replace",
        action="store_true",
        help="reinstall this host at next reboot",
    )
    p.add_option(
        "-D",
        "--display",
        dest="is_display",
        action="store_true",
        help="display the configuration stored in cobbler for the given object",
    )
    p.add_option("-p", "--profile", dest="profile", help="use this cobbler profile")
    p.add_option("-y", "--system", dest="system", help="use this cobbler system")
    p.add_option("-i", "--image", dest="image", help="use this cobbler image")
    p.add_option(
        "-s",
        "--server",
        dest="server",
        default=os.environ.get("COBBLER_SERVER", ""),
        help="attach to this cobbler server",
    )
    p.add_option(
        "-S",
        "--static-interface",
        dest="static_interface",
        help="use static network configuration from this interface while installing",
    )
    p.add_option("-t", "--port", dest="port", help="cobbler port (default 80)")
    p.add_option(
        "-w",
        "--vm-poll",
        dest="should_poll",
        action="store_true",
        help="for xen/qemu/KVM, poll & restart the VM after the install is done",
    )
    p.add_option(
        "-P", "--virt-path", dest="virt_path", help="override virt install location"
    )
    p.add_option(
        "",
        "--force-path",
        dest="force_path",
        action="store_true",
        help="Force overwrite of virt install location",
    )
    p.add_option(
        "-T", "--virt-type", dest="virt_type", help="override virt install type"
    )
    p.add_option("-B", "--virt-bridge", dest="virt_bridge", help="override virt bridge")
    p.add_option(
        "-n",
        "--nogfx",
        action="store_true",
        dest="no_gfx",
        help="disable Xen graphics (xenpv,xenfv)",
    )
    p.add_option(
        "-g",
        "--graphics",
        dest="gfx_type",
        default="vnc",
        help="specify the graphics type: vnc, sdl, spice, none",
    )
    p.add_option(
        "",
        "--virt-auto-boot",
        action="store_true",
        dest="virt_auto_boot",
        help="set VM for autoboot",
    )
    p.add_option(
        "",
        "--virt-pxe-boot",
        action="store_true",
        dest="virt_pxe_boot",
        help="PXE boot for installation override",
    )
    p.add_option(
        "",
        "--add-reinstall-entry",
        dest="add_reinstall_entry",
        action="store_true",
        help="when used with --replace-self, just add entry to grub, \
        do not make it the default",
    )
    p.add_option(
        "-C",
        "--livecd",
        dest="live_cd",
        action="store_true",
        help="used by the custom livecd only, not for humans",
    )
    p.add_option(
        "",
        "--kexec",
        dest="use_kexec",
        action="store_true",
        help="Instead of writing a new bootloader config when using --replace-self, just kexec the new kernel and "
        "initrd ",
    )
    p.add_option(
        "",
        "--no-copy-default",
        dest="no_copy_default",
        action="store_true",
        help="Do not copy the kernel args from the default kernel entry when using --replace-self",
    )
    p.add_option(
        "",
        "--embed",
        dest="embed_autoinst",
        action="store_true",
        help="When used with  --replace-self, embed the autoinst in the initrd to overcome potential DHCP timeout "
        "issues. (seldom needed) ",
    )
    p.add_option(
        "",
        "--qemu-disk-type",
        dest="qemu_disk_type",
        help="when used with --virt_type=qemu, add select of disk driver types: ide,scsi,virtio",
    )
    p.add_option(
        "",
        "--qemu-net-type",
        dest="qemu_net_type",
        help="when used with --virt_type=qemu, select type of network device to use: e1000, ne2k_pci, pcnet, rtl8139, "
        "virtio ",
    )
    p.add_option(
        "",
        "--qemu-machine-type",
        dest="qemu_machine_type",
        help="when used with --virt_type=qemu, select type of machine type to emulate: pc, pc-1.0, pc-0.15",
    )
    p.add_option(
        "",
        "--wait",
        # default to 0 for koan backwards compatibility
        dest="wait",
        type="int",
        default=0,
        help="pass the --wait=<INT> argument to virt-install",
    )
    p.add_option(
        "",
        "--noreboot",
        # default to False for koan backwards compatibility
        dest="noreboot",
        default=False,
        action="store_true",
        help="pass the --noreboot argument to virt-install",
    )
    p.add_option(
        "",
        "--import",
        # default to False for koan backwards compatibility
        dest="osimport",
        default=False,
        action="store_true",
        help="pass the --import argument to virt-install",
    )

    options, args = p.parse_args()

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

    p = OptionParser()
    p.add_option(
        "-s",
        "--server",
        dest="server",
        default=os.environ.get("COBBLER_SERVER", ""),
        help="attach to this cobbler server",
    )
    p.add_option(
        "-f",
        "--fqdn",
        dest="hostname",
        default="",
        help="override the discovered hostname",
    )
    p.add_option(
        "-p", "--port", dest="port", default="80", help="cobbler port (default 80)"
    )
    p.add_option(
        "-P",
        "--profile",
        dest="profile",
        default="",
        help="assign this profile to this system",
    )
    p.add_option(
        "-b",
        "--batch",
        dest="batch",
        action="store_true",
        help="indicates this is being run from a script",
    )

    options, args = p.parse_args()
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
