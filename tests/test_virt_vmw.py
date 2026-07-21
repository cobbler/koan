import pytest

from koan.cexceptions import InfoException, VirtCreateException
from koan.virt import vmw
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "rc,expected_exception",
    [
        (0, does_not_raise()),
        (1, pytest.raises(VirtCreateException)),
    ],
)
def test_make_disk(rc, expected_exception, mocker):
    # Arrange
    os_system = mocker.patch("koan.virt.vmw.os.system", return_value=rc)

    # Act
    with expected_exception:
        vmw.make_disk(10, "/var/lib/vmware/images/foo")

    # Assert
    os_system.assert_called_once()
    cmd = os_system.call_args[0][0]
    assert "vmware-vdiskmanager" in cmd
    assert "10Gb" in cmd
    assert "/var/lib/vmware/images/foo" in cmd


def test_make_vmx_writes_template(mocker):
    # Arrange
    mock_open = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)

    # Act
    vmw.make_vmx(
        "/var/lib/vmware/vmx/foo",
        "/var/lib/vmware/images/foo",
        "foo",
        "AA:BB:CC:DD:EE:FF",
        "512",
    )

    # Assert
    mock_open.assert_called_once_with("/var/lib/vmware/vmx/foo", "w+")
    handle = mock_open()
    handle.write.assert_called_once()
    written = handle.write.call_args[0][0]
    assert 'Ethernet0.Address = "aa:bb:cc:dd:ee:ff"' in written
    assert 'scsi0:0.filename = "/var/lib/vmware/images/foo"' in written
    assert 'displayName = "foo"' in written
    assert 'memsize = "512"' in written
    handle.close.assert_called_once()


@pytest.mark.parametrize(
    "rc,expected_exception",
    [
        (0, does_not_raise()),
        (1, pytest.raises(VirtCreateException)),
    ],
)
def test_register_vmx(rc, expected_exception, mocker):
    # Arrange
    os_system = mocker.patch("koan.virt.vmw.os.system", return_value=rc)

    # Act
    with expected_exception:
        vmw.register_vmx("/var/lib/vmware/vmx/foo")

    # Assert
    os_system.assert_called_once()
    cmd = os_system.call_args[0][0]
    assert "vmware-cmd -s register" in cmd
    assert "/var/lib/vmware/vmx/foo" in cmd


@pytest.mark.parametrize(
    "rc,expected_exception",
    [
        (0, does_not_raise()),
        (1, pytest.raises(VirtCreateException)),
    ],
)
def test_start_vm(rc, expected_exception, mocker):
    # Arrange
    os_chmod = mocker.patch("koan.virt.vmw.os.chmod")
    os_system = mocker.patch("koan.virt.vmw.os.system", return_value=rc)

    # Act
    with expected_exception:
        vmw.start_vm("/var/lib/vmware/vmx/foo")

    # Assert
    os_chmod.assert_called_once_with("/var/lib/vmware/vmx/foo", 0o755)
    os_system.assert_called_once()
    cmd = os_system.call_args[0][0]
    assert "vmware-cmd" in cmd
    assert "start" in cmd


def test_start_install_raises_on_image_profile():
    # Arrange
    profile_data = {"file": "/some/image"}

    # Act / Assert
    with pytest.raises(InfoException):
        vmw.start_install(profile_data=profile_data)


def test_start_install_returns_1_when_no_interfaces():
    # Arrange
    profile_data = {}

    # Act
    result = vmw.start_install(profile_data=profile_data)

    # Assert
    assert result == 1


def test_start_install_returns_1_when_no_mac_found():
    # Arrange
    profile_data = {"interfaces": {"eth0": {"mac_address": None}}}

    # Act
    result = vmw.start_install(profile_data=profile_data)

    # Assert
    assert result == 1


def test_start_install_raises_when_not_exactly_one_disk(mocker):
    # Arrange
    mocker.patch("koan.virt.vmw.os.path.exists", return_value=True)
    profile_data = {"interfaces": {"eth0": {"mac_address": "AA:BB:CC:DD:EE:FF"}}}

    # Act / Assert
    with pytest.raises(VirtCreateException):
        vmw.start_install(
            name="foo",
            ram=512,
            disks=[],
            profile_data=profile_data,
        )


def test_start_install_happy_path_creates_dirs(mocker):
    # Arrange
    os_path_exists = mocker.patch("koan.virt.vmw.os.path.exists", return_value=False)
    os_makedirs = mocker.patch("koan.virt.vmw.os.makedirs")
    make_disk = mocker.patch("koan.virt.vmw.make_disk")
    make_vmx = mocker.patch("koan.virt.vmw.make_vmx")
    register_vmx = mocker.patch("koan.virt.vmw.register_vmx")
    start_vm = mocker.patch("koan.virt.vmw.start_vm")

    profile_data = {"interfaces": {"eth0": {"mac_address": "AA:BB:CC:DD:EE:FF"}}}
    disks = [("/dev/whatever", 10)]

    # Act
    result = vmw.start_install(
        name="foo",
        ram=512,
        disks=disks,
        profile_data=profile_data,
    )

    # Assert
    assert result is None
    assert os_path_exists.call_count == 2
    os_path_exists.assert_any_call(vmw.IMAGE_DIR)
    os_path_exists.assert_any_call(vmw.VMX_DIR)
    os_makedirs.assert_any_call(vmw.IMAGE_DIR)
    os_makedirs.assert_any_call(vmw.VMX_DIR)

    image = "%s/foo" % vmw.IMAGE_DIR
    vmx = "%s/foo" % vmw.VMX_DIR

    make_disk.assert_called_once_with(10, image)
    make_vmx.assert_called_once_with(vmx, image, "foo", "AA:BB:CC:DD:EE:FF", 512)
    register_vmx.assert_called_once_with(vmx)
    start_vm.assert_called_once_with(vmx)


def test_start_install_does_not_create_dirs_when_they_exist(mocker):
    # Arrange
    mocker.patch("koan.virt.vmw.os.path.exists", return_value=True)
    os_makedirs = mocker.patch("koan.virt.vmw.os.makedirs")
    mocker.patch("koan.virt.vmw.make_disk")
    mocker.patch("koan.virt.vmw.make_vmx")
    mocker.patch("koan.virt.vmw.register_vmx")
    mocker.patch("koan.virt.vmw.start_vm")

    profile_data = {"interfaces": {"eth0": {"mac_address": "AA:BB:CC:DD:EE:FF"}}}
    disks = [("/dev/whatever", 10)]

    # Act
    vmw.start_install(
        name="foo",
        ram=512,
        disks=disks,
        profile_data=profile_data,
    )

    # Assert
    os_makedirs.assert_not_called()
