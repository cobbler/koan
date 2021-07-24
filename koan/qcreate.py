"""
Virtualization installation functions.

Copyright 2007-2008 Red Hat, Inc and Others.
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA

module for creating fullvirt guests via KVM/kqemu/qemu
requires python-virtinst-0.200 (or virt-install in later distros).
"""

from xml.dom.minidom import parseString

from koan.cexceptions import InfoException
from koan import utils
from koan import virtinstall


def start_install(*args, **kwargs):
    if 'arch' in kwargs.keys():
        kwargs['arch'] = None  # use host arch for kvm acceleration
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
        if 'type' in attributes.keys() and attributes['type'] == 'kvm':
            kwargs['virt_type'] = 'kvm'
            break

    virtinstall.create_image_file(*args, **kwargs)
    cmd = virtinstall.build_commandline("qemu:///system", *args, **kwargs)
    rc, result, result_stderr = utils.subprocess_get_response(cmd, ignore_rc=True, get_stderr=True)
    if rc != 0:
        raise InfoException("command failed (%s): %s %s" % (rc, result, result_stderr))
