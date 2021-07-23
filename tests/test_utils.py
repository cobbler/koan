import subprocess
from unittest.mock import MagicMock

import distro
import pytest

from koan import utils
from tests.conftest import does_not_raise


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


@pytest.mark.parametrize("os_path_return", [
    (True),
    (False)
])
def test_is_uefi_system(os_path_return, mocker):
    # Arrange
    mocker.patch("os.path.exists", return_value=os_path_return)

    # Act
    result = utils.is_uefi_system()

    # Assert
    assert result is os_path_return


@pytest.mark.parametrize("shutil_which_return,expected_exception", [
    ("/usr/bin/grub2-mkrelpath", does_not_raise()),
    (None, pytest.raises(RuntimeError))
])
def test_get_grub2_mkrelpath_executable(shutil_which_return, expected_exception, mocker):
    # Arrange
    mocker.patch("shutil.which", return_value=shutil_which_return)

    # Act
    with expected_exception:
        result = utils.get_grub2_mkrelpath_executable()

        # Assert
        assert result == shutil_which_return


@pytest.mark.parametrize("mocked_process_result,mocked_os_path_exists,expected_exception", [
    (subprocess.CompletedProcess(args="", returncode=0, stdout="Test\n"), True, does_not_raise()),
    (subprocess.CompletedProcess(args="", returncode=1, stdout="Test\n"), True, pytest.raises(RuntimeError)),
    (None, False, pytest.raises(FileNotFoundError))
])
def test_get_grub_real_path(mocked_process_result, mocked_os_path_exists, expected_exception, mocker):
    # Arrange
    mocker.patch("subprocess.run", return_value=mocked_process_result)
    mocker.patch("os.path.exists", return_value=mocked_os_path_exists)
    mocker.patch("koan.utils.get_grub2_mkrelpath_executable", return_value="/bin/sh")

    # Act
    with expected_exception:
        result = utils.get_grub_real_path("/bin/sh")

        # Assert
        assert result == mocked_process_result.stdout.strip()
