from unittest.mock import MagicMock

import distro
import pytest

from koan import utils


@pytest.mark.parametrize("test_input,expected",
                         [("suse", "suse"), ("rhel", "redhat"), ("centos", "centos"), ("notexisting", "unknown")])
def test_os_release(test_input, expected):
    # Arrange
    distro.id = MagicMock(return_value=test_input)
    distro.like = MagicMock(return_value=test_input)
    distro.version = MagicMock(return_value=11)

    # Act
    resname, resnumber = utils.os_release()

    # Assert
    assert resname == expected


def test_is_uefi_system():
    # Arrange
    # Act
    result = utils.is_uefi_system()

    # Assert
    assert result


def test_get_grub2_mkrelpath_executable():
    # Arrange
    # Act
    result = utils.get_grub2_mkrelpath_executable()

    # Assert
    assert result == "/usr/bin/grub2-mkrelpath"


def test_get_grub_real_path():
    # Arrange
    # Act
    result = utils.get_grub_real_path("/bin/sh")

    # Assert
    assert result == "/@/.snapshots/1/snapshot/usr/bin/bash"
