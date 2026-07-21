import re
import subprocess
from unittest.mock import MagicMock, mock_open

import distro
import netifaces
import pytest

from koan import utils
from koan.cexceptions import InfoException
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("suse", "suse"),
        ("rhel", "redhat"),
        ("centos", "centos"),
        ("notexisting", "unknown"),
    ],
)
def test_os_release(test_input, expected):
    # Arrange
    distro.id = MagicMock(return_value=test_input)
    distro.like = MagicMock(return_value=test_input)
    distro.version = MagicMock(return_value=11)

    # Act
    resname, resnumber = utils.os_release()

    # Assert
    assert resname == expected


@pytest.mark.parametrize("os_path_return", [(True), (False)])
def test_is_uefi_system(os_path_return, mocker):
    # Arrange
    mocker.patch("os.path.exists", return_value=os_path_return)

    # Act
    result = utils.is_uefi_system()

    # Assert
    assert result is os_path_return


@pytest.mark.parametrize(
    "shutil_which_return,expected_exception",
    [
        ("/usr/bin/grub2-mkrelpath", does_not_raise()),
        (None, pytest.raises(RuntimeError)),
    ],
)
def test_get_grub2_mkrelpath_executable(
    shutil_which_return, expected_exception, mocker
):
    # Arrange
    mocker.patch("shutil.which", return_value=shutil_which_return)

    # Act
    with expected_exception:
        result = utils.get_grub2_mkrelpath_executable()

        # Assert
        assert result == shutil_which_return


@pytest.mark.parametrize(
    "mocked_process_result,mocked_os_path_exists,expected_exception",
    [
        (
            subprocess.CompletedProcess(args="", returncode=0, stdout="Test\n"),
            True,
            does_not_raise(),
        ),
        (
            subprocess.CompletedProcess(args="", returncode=1, stdout="Test\n"),
            True,
            pytest.raises(RuntimeError),
        ),
        (None, False, pytest.raises(FileNotFoundError)),
    ],
)
def test_get_grub_real_path(
    mocked_process_result, mocked_os_path_exists, expected_exception, mocker
):
    # Arrange
    mocker.patch("subprocess.run", return_value=mocked_process_result)
    mocker.patch("os.path.exists", return_value=mocked_os_path_exists)
    mocker.patch("koan.utils.get_grub2_mkrelpath_executable", return_value="/bin/sh")

    # Act
    with expected_exception:
        result = utils.get_grub_real_path("/bin/sh")

        # Assert
        assert result == mocked_process_result.stdout.strip()


# ---------------------------------------------------------------------------
# input_string_or_dict / dict_to_string
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "test_input,delim,allow_multiples,expected",
    [
        (None, None, True, {}),
        ("", None, True, {}),
        ("a=1 b=2", None, True, {"a": "1", "b": "2"}),
        ("a=1,b=2", ",", True, {"a": "1", "b": "2"}),
        ("foo", None, True, {"foo": None}),
        ("a=1 a=2", None, True, {"a": ["1", "2"]}),
        ("a=1 a=2 a=3", None, True, {"a": ["1", "2", "3"]}),
        ("a=1 a=2", None, False, {"a": "2"}),
        ("a=1,,b=2", ",", True, {"a": "1", "b": "2"}),
        ({"a": "1", "": "x"}, None, True, {"a": "1"}),
        ({}, None, True, {}),
    ],
)
def test_input_string_or_dict(test_input, delim, allow_multiples, expected):
    # Act
    result = utils.input_string_or_dict(
        test_input, delim=delim, allow_multiples=allow_multiples
    )

    # Assert
    assert result == expected


@pytest.mark.parametrize("invalid_input", [["a", "b"], 42, 3.14])
def test_input_string_or_dict_raises_on_invalid_type(invalid_input):
    # Act & Assert
    with pytest.raises(InfoException):
        utils.input_string_or_dict(invalid_input)


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ({}, ""),
        ({"foo": None}, "foo "),
        ({"foo": "bar"}, "foo=bar "),
        ({"foo": ["1", "2"]}, "foo=1 foo=2 "),
        ("already a string", "already a string"),
    ],
)
def test_dict_to_string(test_input, expected):
    # Act
    result = utils.dict_to_string(test_input)

    # Assert
    assert result == expected


def test_dict_to_string_and_input_string_or_dict_roundtrip():
    # Arrange
    original = {"a": "1"}

    # Act
    as_string = utils.dict_to_string(original)
    back_to_dict = utils.input_string_or_dict(as_string)

    # Assert
    assert back_to_dict == original


# ---------------------------------------------------------------------------
# uniqify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "test_input,purge,expected",
    [
        ([], None, []),
        (["a", "b", "a", "c"], None, ["a", "b", "c"]),
        (["a", "b", "a", "c"], "b", ["a", "c"]),
        ([1, 1, 2], None, [1, 2]),
    ],
)
def test_uniqify(test_input, purge, expected):
    # Act
    result = utils.uniqify(test_input, purge=purge)

    # Assert
    assert result == expected


# ---------------------------------------------------------------------------
# check_version_greater_or_equal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version1,version2,expected",
    [
        ("19.19.19", "2.2.2", True),
        ("1.19.19", "2.2.2", False),
        ("2.19.19", "2.2.2", True),
        ("2.2.19", "2.2.2", True),
        ("1.1.0", "2.2.2", False),
        ("1.2.1", "2.2.2", False),
        ("2.2.2", "2.2.2", True),
    ],
)
def test_check_version_greater_or_equal(version1, version2, expected):
    # Act
    result = utils.check_version_greater_or_equal(version1, version2)

    # Assert
    assert result == expected


def test_check_version_greater_or_equal_mismatched_format_raises():
    # Act & Assert
    with pytest.raises(Exception):
        utils.check_version_greater_or_equal("1.2", "1.2.3")


# ---------------------------------------------------------------------------
# random_mac
# ---------------------------------------------------------------------------


def test_random_mac_format():
    # Act
    result = utils.random_mac()

    # Assert
    assert re.match(r"^00:50:56:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}$", result)


def test_random_mac_is_callable_multiple_times():
    # Act
    results = {utils.random_mac() for _ in range(5)}

    # Assert
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# subprocess_call / subprocess_get_response
# ---------------------------------------------------------------------------


def test_subprocess_call_success(mocker):
    # Arrange
    mocker.patch("subprocess.call", return_value=0)

    # Act
    result = utils.subprocess_call(["echo", "hi"])

    # Assert
    assert result == 0


def test_subprocess_call_nonzero_raises(mocker):
    # Arrange
    mocker.patch("subprocess.call", return_value=1)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.subprocess_call(["false"])


def test_subprocess_call_nonzero_ignored(mocker):
    # Arrange
    mocker.patch("subprocess.call", return_value=1)

    # Act
    result = utils.subprocess_call(["false"], ignore_rc=1)

    # Assert
    assert result == 1


def test_subprocess_get_response_success(mocker):
    # Arrange
    mock_popen = MagicMock()
    mock_popen.communicate.return_value = (b"stdout-data", b"")
    mock_popen.wait.return_value = 0
    mocker.patch("subprocess.Popen", return_value=mock_popen)

    # Act
    rc, result = utils.subprocess_get_response(["ls"])

    # Assert
    assert rc == 0
    assert result == "stdout-data"


def test_subprocess_get_response_with_stderr(mocker):
    # Arrange
    mock_popen = MagicMock()
    mock_popen.communicate.return_value = (b"out", b"errdata")
    mock_popen.wait.return_value = 0
    mocker.patch("subprocess.Popen", return_value=mock_popen)

    # Act
    rc, result, stderr_result = utils.subprocess_get_response(["ls"], get_stderr=True)

    # Assert
    assert rc == 0
    assert result == "out"
    assert stderr_result == "errdata"


def test_subprocess_get_response_nonzero_raises(mocker):
    # Arrange
    mock_popen = MagicMock()
    mock_popen.communicate.return_value = (b"", b"")
    mock_popen.wait.return_value = 1
    mocker.patch("subprocess.Popen", return_value=mock_popen)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.subprocess_get_response(["false"])


def test_subprocess_get_response_nonzero_ignored(mocker):
    # Arrange
    mock_popen = MagicMock()
    mock_popen.communicate.return_value = (b"data", b"")
    mock_popen.wait.return_value = 1
    mocker.patch("subprocess.Popen", return_value=mock_popen)

    # Act
    rc, result = utils.subprocess_get_response(["false"], ignore_rc=True)

    # Assert
    assert rc == 1
    assert result == "data"


# ---------------------------------------------------------------------------
# urlread / urlgrab
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_url", [None, ""])
def test_urlread_invalid_url_raises(bad_url):
    # Act & Assert
    with pytest.raises(InfoException):
        utils.urlread(bad_url)


def test_urlread_nfs_success(mocker):
    # Arrange
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/koan_nfsXXXX")
    mocker.patch("koan.utils.subprocess_call")
    mocker.patch("builtins.open", mock_open(read_data="filedata"))

    # Act
    result = utils.urlread("nfs://server:/path/to/file.txt")

    # Assert
    assert result == "filedata"
    assert utils.subprocess_call.call_count == 2


def test_urlread_nfs_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/koan_nfsXXXX")
    mocker.patch("koan.utils.subprocess_call", side_effect=Exception("mount failed"))

    # Act & Assert
    with pytest.raises(InfoException):
        utils.urlread("nfs://server:/path/to/file.txt")


def test_urlread_http_success(mocker):
    # Arrange
    fd = MagicMock()
    fd.read.return_value = b"webdata"
    mocker.patch("urllib.request.urlopen", return_value=fd)

    # Act
    result = utils.urlread("http://example.com/file")

    # Assert
    assert result == b"webdata"
    fd.close.assert_called_once()


def test_urlread_http_failure_raises(mocker):
    # Arrange
    mocker.patch("urllib.request.urlopen", side_effect=Exception("network error"))

    # Act & Assert
    with pytest.raises(InfoException):
        utils.urlread("http://example.com/file")


def test_urlread_file_success(mocker):
    # Arrange
    mocker.patch("builtins.open", mock_open(read_data="filecontent"))

    # Act
    result = utils.urlread("file:///tmp/x.txt")

    # Assert
    assert result == "filecontent"


def test_urlread_file_failure_raises(mocker):
    # Arrange
    mocker.patch("builtins.open", side_effect=OSError("no such file"))

    # Act & Assert
    with pytest.raises(InfoException):
        utils.urlread("file:///tmp/does_not_exist.txt")


def test_urlread_unhandled_protocol_raises():
    # Act & Assert
    with pytest.raises(InfoException):
        utils.urlread("ftp://example.com/file")


def test_urlgrab_writes_downloaded_data(mocker):
    # Arrange
    mocker.patch("koan.utils.urlread", return_value=b"content")
    m = mock_open()
    mocker.patch("builtins.open", m)

    # Act
    utils.urlgrab("http://example.com/file", "/tmp/saveto")

    # Assert
    m.assert_called_once_with("/tmp/saveto", "w+b")
    m.return_value.write.assert_called_once_with(b"content")


# ---------------------------------------------------------------------------
# get_network_info
# ---------------------------------------------------------------------------


def test_get_network_info(mocker):
    # Arrange
    def fake_ifaddresses(iname):
        data = {
            "eth0": {
                netifaces.AF_LINK: [{"addr": "aa:bb:cc:dd:ee:ff"}],
                netifaces.AF_INET: [
                    {"addr": "192.168.1.5", "netmask": "255.255.255.0"}
                ],
            },
            "lo": {
                netifaces.AF_LINK: [{"addr": "00:00:00:00:00:00"}],
                netifaces.AF_INET: [{"addr": "127.0.0.1", "netmask": "255.0.0.0"}],
            },
            "eth1": {
                netifaces.AF_LINK: [{"addr": "11:22:33:44:55:66"}],
            },
        }
        return data[iname]

    mocker.patch("netifaces.interfaces", return_value=["eth0", "lo", "eth1"])
    mocker.patch("netifaces.ifaddresses", side_effect=fake_ifaddresses)

    # Act
    result = utils.get_network_info()

    # Assert
    assert result["eth0"] == {
        "ip_address": "192.168.1.5",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "netmask": "255.255.255.0",
        "bridge": 0,
        "module": "",
    }
    assert result["lo"]["mac_address"] == "?"
    assert result["lo"]["ip_address"] == "?"
    assert result["eth1"]["ip_address"] == "?"
    assert result["eth1"]["netmask"] == "?"


# ---------------------------------------------------------------------------
# connect_to_server
# ---------------------------------------------------------------------------


def test_connect_to_server_no_server_raises(mocker):
    # Arrange
    mocker.patch("os.environ.get", return_value="")

    # Act & Assert
    with pytest.raises(InfoException):
        utils.connect_to_server(server=None)


def test_connect_to_server_success(mocker):
    # Arrange
    mock_proxy = MagicMock()
    mock_proxy.extended_version.return_value = {"version_tuple": [4, 0, 0]}
    mocker.patch("xmlrpc.client.ServerProxy", return_value=mock_proxy)

    # Act
    result = utils.connect_to_server(server="myserver")

    # Assert
    assert result is mock_proxy
    mock_proxy.ping.assert_called_once()


def test_connect_to_server_uses_custom_port(mocker):
    # Arrange
    mock_proxy = MagicMock()
    mock_proxy.extended_version.return_value = {"version_tuple": [4, 0, 0]}
    mock_server_proxy = mocker.patch(
        "xmlrpc.client.ServerProxy", return_value=mock_proxy
    )

    # Act
    utils.connect_to_server(server="myserver", port=25151)

    # Assert
    mock_server_proxy.assert_any_call("https://myserver:25151/cobbler_api")


def test_connect_to_server_all_urls_fail_raises(mocker):
    # Arrange
    mocker.patch(
        "xmlrpc.client.ServerProxy", side_effect=Exception("connection refused")
    )

    # Act & Assert
    with pytest.raises(InfoException):
        utils.connect_to_server(server="myserver")


def test_connect_to_server_refuses_old_version(mocker):
    # Arrange
    mock_proxy = MagicMock()
    mock_proxy.extended_version.return_value = {"version_tuple": [3, 3, 3]}
    mocker.patch("xmlrpc.client.ServerProxy", return_value=mock_proxy)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.connect_to_server(server="myserver")


def test_connect_to_server_accepts_exact_minimum_version(mocker):
    # Arrange
    mock_proxy = MagicMock()
    mock_proxy.extended_version.return_value = {"version_tuple": [4, 0, 0]}
    mocker.patch("xmlrpc.client.ServerProxy", return_value=mock_proxy)

    # Act
    result = utils.connect_to_server(server="myserver")

    # Assert
    assert result is mock_proxy


def test_connect_to_server_accepts_newer_version(mocker):
    # Arrange
    mock_proxy = MagicMock()
    mock_proxy.extended_version.return_value = {"version_tuple": [4, 1, 2]}
    mocker.patch("xmlrpc.client.ServerProxy", return_value=mock_proxy)

    # Act
    result = utils.connect_to_server(server="myserver")

    # Assert
    assert result is mock_proxy


def test_connect_to_server_refuses_when_extended_version_rpc_fails(mocker):
    # Arrange
    import xmlrpc.client as xmlrpclib

    mock_proxy = MagicMock()
    mock_proxy.extended_version.side_effect = xmlrpclib.Fault(1, "no such method")
    mocker.patch("xmlrpc.client.ServerProxy", return_value=mock_proxy)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.connect_to_server(server="myserver")


# ---------------------------------------------------------------------------
# create_xendomains_symlink
# ---------------------------------------------------------------------------


def test_create_xendomains_symlink_dst_exists(mocker):
    # Arrange
    mocker.patch("os.path.exists", return_value=True)

    # Act
    result = utils.create_xendomains_symlink("myvm")

    # Assert
    assert result is False


def test_create_xendomains_symlink_dst_not_writable(mocker):
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.access", return_value=False)

    # Act
    result = utils.create_xendomains_symlink("myvm")

    # Assert
    assert result is False


def test_create_xendomains_symlink_src_missing(mocker):
    # Arrange
    mocker.patch("os.path.exists", side_effect=[False, False])
    mocker.patch("os.access", return_value=True)

    # Act
    result = utils.create_xendomains_symlink("myvm")

    # Assert
    assert result is False


def test_create_xendomains_symlink_success(mocker):
    # Arrange
    mocker.patch("os.path.exists", side_effect=[False, True])
    mocker.patch("os.access", return_value=True)
    mock_symlink = mocker.patch("os.symlink")

    # Act
    result = utils.create_xendomains_symlink("myvm")

    # Assert
    assert result is True
    mock_symlink.assert_called_once_with("/etc/xen/myvm", "/etc/xen/auto/myvm")


# ---------------------------------------------------------------------------
# sync_file
# ---------------------------------------------------------------------------


def test_sync_file(mocker):
    # Arrange
    mock_call = mocker.patch("subprocess.call")
    mock_copy = mocker.patch("shutil.copy")
    mock_chmod = mocker.patch("os.chmod")
    mock_chown = mocker.patch("os.chown")

    # Act
    utils.sync_file("/etc/foo.orig", "/etc/foo.new", 0, 0, 0o644)

    # Assert
    mock_call.assert_called_once_with(
        ["/usr/bin/diff", "/etc/foo.orig", "/etc/foo.new"]
    )
    mock_copy.assert_called_once_with("/etc/foo.new", "/etc/foo.orig")
    mock_chmod.assert_called_once_with("/etc/foo.orig", 0o644)
    mock_chown.assert_called_once_with("/etc/foo.orig", 0, 0)


# ---------------------------------------------------------------------------
# create_qemu_image_file
# ---------------------------------------------------------------------------


def test_create_qemu_image_file_invalid_driver_raises(mocker):
    # Arrange
    mock_subprocess_call = mocker.patch("koan.utils.subprocess_call")

    # Act & Assert
    with pytest.raises(InfoException):
        utils.create_qemu_image_file("/tmp/disk.img", 10, "notadriver")
    mock_subprocess_call.assert_not_called()


@pytest.mark.parametrize("driver_type", ["raw", "qcow", "qcow2", "vmdk", "qed"])
def test_create_qemu_image_file_success(driver_type, mocker):
    # Arrange
    mock_subprocess_call = mocker.patch("koan.utils.subprocess_call")

    # Act
    utils.create_qemu_image_file("/tmp/disk.img", 10, driver_type)

    # Assert
    mock_subprocess_call.assert_called_once_with(
        ["qemu-img", "create", "-f", driver_type, "/tmp/disk.img", "10G"]
    )


def test_create_qemu_image_file_subprocess_failure_raises(mocker):
    # Arrange
    mocker.patch(
        "koan.utils.subprocess_call", side_effect=InfoException("command failed")
    )

    # Act & Assert
    with pytest.raises(InfoException):
        utils.create_qemu_image_file("/tmp/disk.img", 10, "raw")


# ---------------------------------------------------------------------------
# libvirt_enable_autostart
# ---------------------------------------------------------------------------


def test_libvirt_enable_autostart_success(mocker):
    # Arrange
    domain = MagicMock()
    domain.autostart = 1
    conn = MagicMock()
    conn.lookupByName.return_value = domain
    mocker.patch("libvirt.open", return_value=conn)

    # Act
    utils.libvirt_enable_autostart("myvm")

    # Assert
    domain.setAutostart.assert_called_once_with(1)


def test_libvirt_enable_autostart_connect_failure_raises(mocker):
    # Arrange
    mocker.patch("libvirt.open", side_effect=Exception("no connection"))

    # Act & Assert
    with pytest.raises(InfoException):
        utils.libvirt_enable_autostart("myvm")


def test_libvirt_enable_autostart_not_enabled_raises(mocker):
    # Arrange
    domain = MagicMock()
    domain.autostart = 0
    conn = MagicMock()
    conn.lookupByName.return_value = domain
    mocker.patch("libvirt.open", return_value=conn)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.libvirt_enable_autostart("myvm")


# ---------------------------------------------------------------------------
# get_vms / find_vm / get_vm_state
# ---------------------------------------------------------------------------


def _make_fake_conn():
    vm1 = MagicMock(name="vm1")
    vm1.name.return_value = "vm1"
    vm2 = MagicMock(name="vm2")
    vm2.name.return_value = "vm2"
    vm3 = MagicMock(name="vm3")
    vm3.name.return_value = "vm3"

    conn = MagicMock()
    conn.listDomainsID.return_value = [1, 2]
    conn.lookupByID.side_effect = lambda id_: {1: vm1, 2: vm2}[id_]
    conn.listDefinedDomains.return_value = ["vm3"]
    conn.lookupByName.return_value = vm3
    return conn, [vm1, vm2, vm3]


def test_get_vms():
    # Arrange
    conn, expected_vms = _make_fake_conn()

    # Act
    result = utils.get_vms(conn)

    # Assert
    assert result == expected_vms


def test_find_vm_found():
    # Arrange
    conn, expected_vms = _make_fake_conn()

    # Act
    result = utils.find_vm(conn, "vm2")

    # Assert
    assert result is expected_vms[1]


def test_find_vm_not_found_raises():
    # Arrange
    conn, _ = _make_fake_conn()

    # Act & Assert
    with pytest.raises(InfoException):
        utils.find_vm(conn, "does-not-exist")


@pytest.mark.parametrize(
    "state_code,expected",
    [
        (0, "running"),
        (3, "paused"),
        (5, "shutdown"),
        (6, "crashed"),
        (99, "unknown"),
    ],
)
def test_get_vm_state(state_code, expected):
    # Arrange
    conn, expected_vms = _make_fake_conn()
    expected_vms[1].info.return_value = [state_code]

    # Act
    result = utils.get_vm_state(conn, "vm2")

    # Assert
    assert result == expected


# ---------------------------------------------------------------------------
# make_floppy
# ---------------------------------------------------------------------------


def test_make_floppy_success(mocker):
    # Arrange
    mocker.patch("tempfile.mkstemp", return_value=(5, "/tmp/floppy123"))
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/mnt123")
    mocker.patch("os.system", return_value=0)
    mock_urlgrab = mocker.patch("koan.utils.urlgrab")

    # Act
    result = utils.make_floppy("http://example.com/ks.cfg")

    # Assert
    assert result == "/tmp/floppy123"
    mock_urlgrab.assert_called_once_with(
        "http://example.com/ks.cfg", "/tmp/mnt123/unattended.txt"
    )


def test_make_floppy_dd_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkstemp", return_value=(5, "/tmp/floppy123"))
    mocker.patch("os.system", return_value=1)

    # Act & Assert
    with pytest.raises(InfoException):
        utils.make_floppy("http://example.com/ks.cfg")


def test_make_floppy_mkdosfs_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkstemp", return_value=(5, "/tmp/floppy123"))
    mocker.patch("os.system", side_effect=[0, 1])

    # Act & Assert
    with pytest.raises(InfoException):
        utils.make_floppy("http://example.com/ks.cfg")


def test_make_floppy_mount_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkstemp", return_value=(5, "/tmp/floppy123"))
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/mnt123")
    mocker.patch("os.system", side_effect=[0, 0, 1])

    # Act & Assert
    with pytest.raises(InfoException):
        utils.make_floppy("http://example.com/ks.cfg")


def test_make_floppy_umount_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkstemp", return_value=(5, "/tmp/floppy123"))
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/mnt123")
    mocker.patch("os.system", side_effect=[0, 0, 0, 1])
    mocker.patch("koan.utils.urlgrab")

    # Act & Assert
    with pytest.raises(InfoException):
        utils.make_floppy("http://example.com/ks.cfg")


# ---------------------------------------------------------------------------
# nfsmount
# ---------------------------------------------------------------------------


def test_nfsmount_success(mocker):
    # Arrange
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/koan_abcd.mnt")
    mocker.patch("subprocess.call", return_value=0)

    # Act
    result = utils.nfsmount("server:/foo/bar/x.img")

    # Assert
    assert result == ("/tmp/koan_abcd.mnt", "x.img")


def test_nfsmount_failure_raises(mocker):
    # Arrange
    mocker.patch("tempfile.mkdtemp", return_value="/tmp/koan_abcd.mnt")
    mocker.patch("subprocess.call", return_value=1)
    mock_rmtree = mocker.patch("shutil.rmtree")

    # Act & Assert
    with pytest.raises(InfoException):
        utils.nfsmount("server:/foo/bar/x.img")
    mock_rmtree.assert_called_once_with("/tmp/koan_abcd.mnt", ignore_errors=True)
