"""
Virtualization installation functions for image based deployment

Copyright 2008 Red Hat, Inc and Others.
Bryan Kearney <bkearney@redhat.com>

Original version based on virt-image
David Lutterkort <dlutter@redhat.com>

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
"""

from . import utils
from . import virtinstall


def start_install(*args, **kwargs):
    cmd = virtinstall.build_commandline("import", *args, **kwargs)
    rc, result, result_stderr = utils.subprocess_get_response(
        cmd, ignore_rc=True, get_stderr=True
    )
    if rc != 0:
        raise utils.InfoException(
            "command failed (%s): %s %s" % (rc, result, result_stderr)
        )
