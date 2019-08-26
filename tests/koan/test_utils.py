from unittest.mock import MagicMock

import distro
import pytest

from koan import utils


@pytest.mark.parametrize("test_input,expected",
                         [("suse", "suse"), ("rhel", "redhat"), ("centos", "centos"), ("notexisting", "unknown")])
def test_os_release(test_input, expected):
    # Arrange
    distro.linux_distribution = MagicMock(return_value=(test_input, 11, "codename"))

    # Act
    resname, resnumber = utils.os_release()

    # Assert
    assert resname == expected
