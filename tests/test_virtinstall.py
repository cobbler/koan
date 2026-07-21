import unittest
from typing import Any, Generator, List
from unittest.mock import patch

import pytest

import koan
import koan.virtinstall
from koan.cexceptions import InfoException
from koan.virtinstall import _sanitize_nics  # pyright: ignore[reportPrivateUsage]
from koan.virtinstall import build_commandline, create_image_file


@pytest.fixture(autouse=True)
def force_new_style_virtinst() -> Generator[None, None, None]:
    """Force a 'new' virt-install so build_commandline() doesn't disable features.

    The expected command lines below were written assuming a truthy
    virtinst_version (i.e. a modern virt-install), so this pins that
    regardless of whether virt-install is actually installed on the machine
    running the tests.
    """
    original = koan.virtinstall.virtinst_version
    koan.virtinstall.virtinst_version = "6.0.0"
    yield
    koan.virtinstall.virtinst_version = original


class OsPathMock:
    _dir_path = [
        "/path/to/imagedir",
    ]
    _exist_files = [
        "/path/to/imagedir/existfile",
    ]

    def isdir(self, path: str) -> bool:
        if path in self._dir_path:
            return True
        return False

    def exists(self, path: str) -> bool:
        if path in self._exist_files:
            return True
        return False


class KoanVirtInstallTest(unittest.TestCase):
    def testXenPVBasic(self) -> None:
        cmd = build_commandline(
            "xen:///",
            name="foo",
            ram=256,
            uuid="ad6611b9-98e4-82c8-827f-051b6b6680d7",
            vcpus=1,
            bridge="br0",
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            virt_type="xenpv",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data={
                "kernel_local": "kernel",
                "initrd_local": "initrd",
                "install_tree": "http://example.com/tree",
            },
            extra="ks=http://example.com/ks.ks",
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --connect xen:/// --name foo --ram 256 --vcpus 1 "
                "--uuid ad6611b9-98e4-82c8-827f-051b6b6680d7 --nographics --paravirt "
                "--boot kernel=kernel,initrd=initrd,kernel_args=ks=http://example.com/ks.ks "
                "--disk path=/tmp/foo1.img,size=8 --disk path=/dev/foo1 "
                "--network bridge=br0 "
                "--wait 0 --noautoconsole"
            ),
        )

    def testXenFVBasic(self) -> None:
        cmd = build_commandline(
            "xen:///",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/dev/foo1", 0)],
            fullvirt=True,
            arch="x86_64",
            bridge="br0,br1",
            virt_type="xenfv",
            profile_data={
                "breed": "redhat",
                "os_version": "fedora14",
                "install_tree": "http://example.com/tree",
                "interfaces": {
                    "eth0": {
                        "interface_type": "na",
                        "mac_address": "11:22:33:44:55:66",
                    },
                    "eth1": {
                        "interface_type": "na",
                        "mac_address": "11:22:33:33:22:11",
                    },
                },
            },
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --connect xen:/// --name foo --ram 256 --vcpus 1 "
                "--nographics --hvm --location http://example.com/tree/ --arch x86_64 "
                "--os-variant fedora14 --disk path=/dev/foo1 "
                "--network bridge=br0,mac=11:22:33:44:55:66 "
                "--network bridge=br1,mac=11:22:33:33:22:11 "
                "--wait 0 --noautoconsole"
            ),
        )

    def testQemuCDROM(self) -> None:
        cmd = build_commandline(
            "qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=True,
            virt_type="qemu",
            bridge="br0",
            profile_data={
                "breed": "windows",
                "file": "/some/cdrom/path.iso",
            },
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --connect qemu:///system --name foo --ram 256 "
                "--vcpus 1 --nographics --virt-type qemu --machine pc --hvm --cdrom /some/cdrom/path.iso "
                "--os-type windows --disk path=/tmp/foo1.img,size=8 "
                "--disk path=/dev/foo1 --network bridge=br0 "
                "--wait 0 --noautoconsole"
            ),
        )

    def testQemuURL(self) -> None:
        cmd = build_commandline(
            "qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=True,
            arch="i686",
            bridge="br0",
            virt_type="qemu",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data={
                "breed": "ubuntu",
                "os_version": "natty",
                "install_tree": "http://example.com/some/install/tree",
            },
            extra="ks=http://example.com/ks.ks text kssendmac",
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --connect qemu:///system --name foo --ram 256 "
                "--vcpus 1 --nographics --virt-type qemu --machine pc --hvm "
                "--location http://example.com/some/install/tree/ "
                "--extra-args=ks=http://example.com/ks.ks text kssendmac "
                "--arch i686 --os-variant ubuntunatty "
                "--disk path=/tmp/foo1.img,size=8,bus=virtio "
                "--disk path=/dev/foo1,bus=virtio "
                "--network bridge=br0,model=virtio --wait 0 --noautoconsole"
            ),
        )

    def testKvmURL(self) -> None:
        cmd = build_commandline(
            "qemu:///system",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/tmp/foo1.img", 8), ("/dev/foo1", 0)],
            fullvirt=None,
            arch="i686",
            bridge="br0",
            virt_type="kvm",
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            qemu_machine_type="pc-1.0",
            profile_data={
                "breed": "ubuntu",
                "os_version": "natty",
                "install_tree": "http://example.com/some/install/tree",
            },
            extra="ks=http://example.com/ks.ks text kssendmac",
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --connect qemu:///system --name foo --ram 256 "
                "--vcpus 1 --nographics --virt-type kvm --machine pc-1.0 "
                "--location http://example.com/some/install/tree/ "
                "--extra-args=ks=http://example.com/ks.ks text kssendmac "
                "--arch i686 --os-variant ubuntunatty "
                "--disk path=/tmp/foo1.img,size=8,bus=virtio "
                "--disk path=/dev/foo1,bus=virtio "
                "--network bridge=br0,model=virtio --wait 0 --noautoconsole"
            ),
        )

    def testImage(self) -> None:
        cmd = build_commandline(
            "import",
            name="foo",
            ram=256,
            vcpus=1,
            fullvirt=True,
            bridge="br0,br2",
            disks=[],
            qemu_driver_type="virtio",
            qemu_net_type="virtio",
            profile_data={
                "file": "/some/install/image.img",
                "network_count": 2,
            },
        )

        cmd = " ".join(cmd)
        self.assertEqual(
            cmd,
            (
                "virt-install --name foo --ram 256 --vcpus 1 --nographics --import "
                "--disk path=/some/install/image.img --network bridge=br0 "
                "--network bridge=br2 --wait 0 --noautoconsole"
            ),
        )

    @patch("koan.virtinstall.utils.subprocess_call")
    @patch("koan.virtinstall.utils.os.path", new_callable=OsPathMock)
    def test_create_qcow_file(self, mock_path: Any, mock_subprocess: Any) -> None:
        disks = [
            ("/path/to/imagedir/new_qcow_file", "30", "qcow"),
            ("/path/to/imagedir/new_qcow2_file", "30", "qcow2"),
            ("/path/to/imagedir/new_raw_file", "30", "raw"),
            ("/path/to/imagedir/new_vmdk_file", "30", "vmdk"),
            ("/path/to/imagedir/new_qcow_file", "30"),
            ("/path/to/imagedir/new_qcow2_file", "0", "qcow2"),
            ("/path/to/imagedir/existfile", "30", "qcow2"),
            ("/path/to/imagedir", "30", "qcow2"),
        ]

        create_image_file(disks)
        res: List[str] = []
        for call_args in mock_subprocess.call_args_list:
            res.append(" ".join(call_args.args[0]))

        self.assertEqual(
            res,
            [
                "qemu-img create -f qcow /path/to/imagedir/new_qcow_file 30G",
                "qemu-img create -f qcow2 /path/to/imagedir/new_qcow2_file 30G",
                "qemu-img create -f raw /path/to/imagedir/new_raw_file 30G",
                "qemu-img create -f vmdk /path/to/imagedir/new_vmdk_file 30G",
            ],
        )


def test_build_commandline_xen_with_image_raises() -> None:
    with pytest.raises(InfoException, match="Xen does not work"):
        build_commandline(
            "xen:///",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[("/dev/foo1", 0)],
            bridge="br0",
            profile_data={"file": "/some/cdrom.iso"},
        )


def test_build_commandline_import_requires_file() -> None:
    with pytest.raises(InfoException, match="Profile 'file' required"):
        build_commandline(
            "import",
            name="foo",
            ram=256,
            vcpus=1,
            disks=[],
            bridge="br0",
            profile_data={},
        )


def test_sanitize_nics_skips_bond_bridge_and_vlan_interfaces() -> None:
    nics = {
        "bond0": {"interface_type": "bond", "mac_address": "aa:aa:aa:aa:aa:aa"},
        "br0": {"interface_type": "bridge", "mac_address": "bb:bb:bb:bb:bb:bb"},
        "eth0.10": {"interface_type": "na", "mac_address": "cc:cc:cc:cc:cc:cc"},
        "eth0": {"interface_type": "na", "mac_address": "dd:dd:dd:dd:dd:dd"},
    }

    result = _sanitize_nics(nics, "br1", "", None)

    assert result == [("br1", "dd:dd:dd:dd:dd:dd")]
