from unittest.mock import MagicMock
import distro

from koan import utils


def test_check_dist():
    # Arrange
    distro.id = MagicMock(return_value="suse")

    # Act
    res = utils.check_dist()

    # Assert
    assert res in ["debian", "suse", "redhat"]


def test_os_release():
    # Arrange
    distro.linux_distribution = MagicMock(return_value="suse")

    # Act
    resname, resnumber = utils.os_release()

    # Assert
    assert resname in ["rhel", "centos", "fedora", "debian", "ubuntu", "suse", "unkown"]
