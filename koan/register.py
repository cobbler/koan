"""
registration tool for cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2009 Red Hat, Inc and Others.
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os
import socket
import time
import traceback

from . import utils
from .cexceptions import InfoException

# usage: cobbler-register [--server=server] [--fqdn=hostname] --profile=foo


class Register:
    def __init__(self):
        """
        Constructor.  Arguments will be filled in by optparse...
        """
        self.server = ""
        self.port = ""
        self.profile = ""
        self.hostname = ""
        self.batch = ""

    def run(self):
        """
        Commence with the registration already.
        """

        # not really required, but probably best that ordinary users don't try
        # to run this not knowing what it does.
        if os.getuid() != 0:
            raise InfoException("root access is required to register")

        print("- preparing to koan home")
        self.conn = utils.connect_to_server(self.server, self.port)
        reg_info = {}
        print("- gathering network info")
        netinfo = utils.get_network_info()
        reg_info["interfaces"] = netinfo
        print("- checking hostname")
        sysname = ""
        if self.hostname != "" and self.hostname != "*AUTO*":
            hostname = self.hostname
            sysname = self.hostname
        else:
            hostname = socket.getfqdn()
            if hostname == "localhost.localdomain":
                if self.hostname == "*AUTO*":
                    hostname = ""
                    sysname = str(time.time())
                else:
                    raise InfoException("must specify --fqdn, could not discover")
            if sysname == "":
                sysname = hostname

        if self.profile == "":
            raise InfoException("must specify --profile")

        # we'll do a profile check here just to avoid some log noise on the remote end.
        # network duplication checks and profile checks also happen on the
        # remote end.

        avail_profiles = self.conn.get_profiles()
        matched_profile = False
        for x in avail_profiles:
            if x.get("name", "") == self.profile:
                matched_profile = True
                break

        reg_info["name"] = sysname
        reg_info["profile"] = self.profile
        reg_info["hostname"] = hostname

        if not matched_profile:
            raise InfoException("no such remote profile, see 'koan --list-profiles'")

        if not self.batch:
            self.conn.register_new_system(reg_info)
            print("- registration successful, new system name: %s" % sysname)
        else:
            try:
                self.conn.register_new_system(reg_info)
                print("- registration successful, new system name: %s" % sysname)
            except:
                traceback.print_exc()
                print("- registration failed, ignoring because of --batch")

        return
