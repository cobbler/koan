"""
Virtualization installation functions.
Currently somewhat Xen/paravirt specific, will evolve later.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: Original version based on virtguest-install
# SPDX-FileCopyrightText: Jeremy Katz <katzj@redhat.com>
# SPDX-FileCopyrightText: Option handling added by Andrew Puch <apuch@redhat.com>
# SPDX-FileCopyrightText: Simplified for use as library by koan, Michael DeHaan <michael.dehaan AT gmail>

from . import utils
from . import virtinstall


def start_install(*args, **kwargs):
    cmd = virtinstall.build_commandline("xen:///", *args, **kwargs)
    rc, result, result_stderr = utils.subprocess_get_response(
        cmd, ignore_rc=True, get_stderr=True
    )
    if rc != 0:
        raise utils.InfoException(
            "command failed (%s): %s %s" % (rc, result, result_stderr)
        )
