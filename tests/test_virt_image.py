import pytest

from koan.cexceptions import InfoException
from koan.virt import image
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "subprocess_response,expected_exception",
    [
        ((0, "ok", ""), does_not_raise()),
        ((1, "", "boom"), pytest.raises(InfoException)),
    ],
)
def test_start_install(subprocess_response, expected_exception, mocker):
    # Arrange
    fake_cmd = ["virt-install", "--foo"]
    build_commandline_mock = mocker.patch(
        "koan.virt.image.virtinstall.build_commandline", return_value=fake_cmd
    )
    subprocess_get_response_mock = mocker.patch(
        "koan.virt.image.utils.subprocess_get_response",
        return_value=subprocess_response,
    )

    # Act
    with expected_exception:
        image.start_install(
            name="test-image",
            ram=512,
            disks=[("/tmp/test.img", 0)],
            vcpus=1,
            profile_data={"file": "/tmp/test.iso"},
        )

    # Assert
    build_commandline_mock.assert_called_once_with(
        "import",
        name="test-image",
        ram=512,
        disks=[("/tmp/test.img", 0)],
        vcpus=1,
        profile_data={"file": "/tmp/test.iso"},
    )
    subprocess_get_response_mock.assert_called_once_with(
        fake_cmd, ignore_rc=True, get_stderr=True
    )
