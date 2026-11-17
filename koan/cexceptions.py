"""
Custom exceptions for Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import Any


class KoanException(Exception):
    def __init__(self, value: str, *args: Any) -> None:
        if args:
            self.value = value % args
        else:
            self.value = value
        # this is a hack to work around some odd exception handling in older pythons
        self.from_koan = 1

    def __str__(self) -> str:
        return repr(self.value)


class KX(KoanException):
    pass


class FileNotFoundException(KoanException):
    pass


class InfoException(Exception):
    """
    Custom exception for tracking of fatal errors.
    """

    def __init__(self, value: str, *args: Any) -> None:
        if args:
            self.value = value % args
        else:
            self.value = value
        self.from_koan = 1

    def __str__(self) -> str:
        return repr(self.value)


class VirtCreateException(Exception):
    pass


class OVZCreateException(Exception):
    pass
