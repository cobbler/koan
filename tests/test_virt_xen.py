from typing import Any

import pytest
from pytest_mock import MockerFixture

from koan.cexceptions import InfoException
from koan.virt import xen
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "subprocess_response,expected_exception",
    [
        ((0, "ok", ""), does_not_raise()),
        ((1, "", "boom"), pytest.raises(InfoException)),
    ],
)
def test_start_install(
    subprocess_response: Any, expected_exception: Any, mocker: MockerFixture
) -> None:
    # Arrange
    fake_cmd = ["virt-install", "--foo"]
    build_commandline_mock = mocker.patch(
        "koan.virt.xen.virtinstall.build_commandline", return_value=fake_cmd
    )
    subprocess_get_response_mock = mocker.patch(
        "koan.virt.xen.utils.subprocess_get_response",
        return_value=subprocess_response,
    )

    # Act
    with expected_exception:
        xen.start_install(
            name="test-xen",
            ram=512,
            disks=[("/tmp/test.img", 1024)],
            vcpus=1,
            profile_data={"install_tree": "http://example.com/install/"},
        )

    # Assert
    build_commandline_mock.assert_called_once_with(
        "xen:///",
        name="test-xen",
        ram=512,
        disks=[("/tmp/test.img", 1024)],
        vcpus=1,
        profile_data={"install_tree": "http://example.com/install/"},
    )
    subprocess_get_response_mock.assert_called_once_with(
        fake_cmd, ignore_rc=True, get_stderr=True
    )
