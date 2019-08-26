from unittest.mock import MagicMock
import distro

from koan import utils


def test_os_release():
    # Arrange
    distro.linux_distribution = MagicMock(return_value=("suse", 11, "codename"))

    # Act
    resname, resnumber = utils.os_release()

    # Assert
    assert resname in ["rhel", "centos", "fedora", "debian", "ubuntu", "suse", "unkown"]
