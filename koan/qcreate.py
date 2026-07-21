"""
Virtualization installation functions.

module for creating fullvirt guests via KVM/kqemu/qemu
requires python-virtinst-0.200 (or virt-install in later distros).
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from xml.dom.minidom import parseString

from koan.cexceptions import InfoException
from koan import utils
from koan import virtinstall


def start_install(*args, **kwargs):
    if "arch" in kwargs.keys():
        kwargs["arch"] = None  # use host arch for kvm acceleration
    # Use kvm acceleration if available
    try:
        import libvirt
    except:
        raise InfoException("package libvirt is required for installing virtual guests")
    conn = libvirt.openReadOnly(None)
    # See http://libvirt.org/formatcaps.html
    capabilities = parseString(conn.getCapabilities())
    for domain in capabilities.getElementsByTagName("domain"):
        attributes = dict(domain.attributes.items())
        if "type" in attributes.keys() and attributes["type"] == "kvm":
            kwargs["virt_type"] = "kvm"
            break

    virtinstall.create_image_file(*args, **kwargs)
    cmd = virtinstall.build_commandline("qemu:///system", *args, **kwargs)
    rc, result, result_stderr = utils.subprocess_get_response(
        cmd, ignore_rc=True, get_stderr=True
    )
    if rc != 0:
        raise InfoException("command failed (%s): %s %s" % (rc, result, result_stderr))
