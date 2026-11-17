"""
Virtualization installation functions for image based deployment
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Bryan Kearney <bkearney@redhat.com>
# SPDX-FileCopyrightText: Original version based on virt-image
# SPDX-FileCopyrightText: David Lutterkort <dlutter@redhat.com>

from typing import Any

from koan import utils, virtinstall


def start_install(*args: Any, **kwargs: Any) -> None:
    cmd = virtinstall.build_commandline("import", *args, **kwargs)
    rc, result, result_stderr = utils.subprocess_get_response(
        cmd, ignore_rc=True, get_stderr=True
    )
    if rc != 0:
        raise utils.InfoException(
            "command failed (%s): %s %s" % (rc, result, result_stderr)
        )
