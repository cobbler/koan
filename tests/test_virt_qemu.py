import sys
from unittest.mock import MagicMock

import pytest

from koan.cexceptions import InfoException
from koan.virt import qemu

CAPABILITIES_WITH_KVM = """<capabilities>
  <host></host>
  <guest>
    <os_type>hvm</os_type>
    <arch name='x86_64'>
      <domain type='qemu'></domain>
      <domain type='kvm'></domain>
    </arch>
  </guest>
</capabilities>"""

CAPABILITIES_WITHOUT_KVM = """<capabilities>
  <host></host>
  <guest>
    <os_type>hvm</os_type>
    <arch name='x86_64'>
      <domain type='qemu'></domain>
    </arch>
  </guest>
</capabilities>"""


def _make_conn(capabilities_xml):
    conn = MagicMock()
    conn.getCapabilities.return_value = capabilities_xml
    return conn


def test_start_install_detects_kvm(mocker):
    # Arrange
    conn = _make_conn(CAPABILITIES_WITH_KVM)
    mocker.patch("libvirt.openReadOnly", return_value=conn)
    create_image_file = mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    build_commandline = mocker.patch(
        "koan.virt.qemu.virtinstall.build_commandline", return_value=["cmd"]
    )
    subprocess_get_response = mocker.patch(
        "koan.virt.qemu.utils.subprocess_get_response", return_value=(0, "", "")
    )

    # Act
    qemu.start_install(virt_type="qemu")

    # Assert
    assert create_image_file.call_args.kwargs["virt_type"] == "kvm"
    assert build_commandline.call_args.kwargs["virt_type"] == "kvm"
    build_commandline.assert_called_once_with("qemu:///system", virt_type="kvm")
    subprocess_get_response.assert_called_once()


def test_start_install_no_kvm_leaves_virt_type_unchanged(mocker):
    # Arrange
    conn = _make_conn(CAPABILITIES_WITHOUT_KVM)
    mocker.patch("libvirt.openReadOnly", return_value=conn)
    create_image_file = mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    build_commandline = mocker.patch(
        "koan.virt.qemu.virtinstall.build_commandline", return_value=["cmd"]
    )
    mocker.patch(
        "koan.virt.qemu.utils.subprocess_get_response", return_value=(0, "", "")
    )

    # Act
    qemu.start_install(virt_type="qemu")

    # Assert
    assert create_image_file.call_args.kwargs["virt_type"] == "qemu"
    assert build_commandline.call_args.kwargs["virt_type"] == "qemu"


def test_start_install_resets_arch_to_none(mocker):
    # Arrange
    conn = _make_conn(CAPABILITIES_WITHOUT_KVM)
    mocker.patch("libvirt.openReadOnly", return_value=conn)
    create_image_file = mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    build_commandline = mocker.patch(
        "koan.virt.qemu.virtinstall.build_commandline", return_value=["cmd"]
    )
    mocker.patch(
        "koan.virt.qemu.utils.subprocess_get_response", return_value=(0, "", "")
    )

    # Act
    qemu.start_install(arch="x86_64")

    # Assert
    assert create_image_file.call_args.kwargs["arch"] is None
    assert build_commandline.call_args.kwargs["arch"] is None


def test_start_install_no_arch_kwarg_not_added(mocker):
    # Arrange
    conn = _make_conn(CAPABILITIES_WITHOUT_KVM)
    mocker.patch("libvirt.openReadOnly", return_value=conn)
    build_commandline = mocker.patch(
        "koan.virt.qemu.virtinstall.build_commandline", return_value=["cmd"]
    )
    mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    mocker.patch(
        "koan.virt.qemu.utils.subprocess_get_response", return_value=(0, "", "")
    )

    # Act
    qemu.start_install()

    # Assert
    assert "arch" not in build_commandline.call_args.kwargs


def test_start_install_libvirt_unavailable_raises_info_exception(mocker):
    # Arrange
    mocker.patch.dict(sys.modules, {"libvirt": None})
    mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    mocker.patch("koan.virt.qemu.virtinstall.build_commandline")
    mocker.patch("koan.virt.qemu.utils.subprocess_get_response")

    # Act / Assert
    with pytest.raises(InfoException, match="libvirt is required"):
        qemu.start_install()


def test_start_install_subprocess_failure_raises_info_exception(mocker):
    # Arrange
    conn = _make_conn(CAPABILITIES_WITHOUT_KVM)
    mocker.patch("libvirt.openReadOnly", return_value=conn)
    mocker.patch("koan.virt.qemu.virtinstall.create_image_file")
    mocker.patch("koan.virt.qemu.virtinstall.build_commandline", return_value=["cmd"])
    mocker.patch(
        "koan.virt.qemu.utils.subprocess_get_response",
        return_value=(1, "out", "err"),
    )

    # Act / Assert
    with pytest.raises(InfoException, match="command failed"):
        qemu.start_install()
