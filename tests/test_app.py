from unittest.mock import MagicMock, call

import pytest

from koan.app import Koan
from koan.cexceptions import InfoException


def test_get_install_tree_from_autoinst_uses_http_server_port(mocker):
    # Arrange
    # Cobbler bakes a non-default http_port into "http_server" (e.g. "host:10080"),
    # while "server" is just the plain hostname/IP koan was invoked with.
    k = Koan()
    k.server = "192.168.10.112"
    k.system = None
    profile_data = {
        "name": "centos7.4-x86_64",
        "autoinst": "http://192.168.10.112:10080/cblr/svc/op/ks/profile/centos7.4-x86_64",
        "http_server": "192.168.10.112:10080",
    }
    mock_urlread = mocker.patch("koan.utils.urlread", return_value=b"")

    # Act
    k.get_install_tree_from_autoinst(profile_data)

    # Assert
    requested_url = mock_urlread.call_args[0][0]
    assert (
        requested_url
        == "http://192.168.10.112:10080/cblr/svc/op/ks/profile/centos7.4-x86_64"
    )


# ---------------------------------------------------------------------------
# GROUP 1 - pure "calculator" methods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hashv,primary_key,alternate_key,default,expected",
    [
        ({"a": 1}, "a", None, None, 1),
        ({"b": 2}, "a", "b", None, 2),
        ({}, "a", "b", "fallback", "fallback"),
        ({}, "a", None, None, None),
        ({"a": 1, "b": 2}, "a", "b", None, 1),
    ],
)
def test_safe_load(hashv, primary_key, alternate_key, default, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.safe_load(hashv, primary_key, alternate_key, default)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "strdata,expected",
    [
        ("server 1.2.3.4 port 80", ["1.2.3.4"]),
        ("no ip in here", []),
        ("1.2.3.4 and 5.6.7.8 both", ["1.2.3.4", "5.6.7.8"]),
    ],
)
def test_get_ips(strdata, expected):
    # Arrange
    k = Koan()

    # Act / Assert
    assert k.get_ips(strdata) == expected


@pytest.mark.parametrize(
    "strdata,expected",
    [
        ("1.2.3.4", True),
        ("no ip here", False),
    ],
)
def test_is_ip(strdata, expected):
    # Arrange
    k = Koan()

    # Act / Assert
    assert k.is_ip(strdata) is expected


@pytest.mark.parametrize(
    "strdata,expected",
    [
        ("aa:bb:cc:dd:ee:ff", ["AA:BB:CC:DD:EE:FF"]),
        ("no mac address here", []),
    ],
)
def test_get_macs(strdata, expected):
    # Arrange
    k = Koan()

    # Act / Assert
    assert k.get_macs(strdata) == expected


@pytest.mark.parametrize(
    "strdata,expected",
    [
        ("AA:BB:CC:DD:EE:FF", True),
        ("not a mac", False),
    ],
)
def test_is_mac(strdata, expected):
    # Arrange
    k = Koan()

    # Act / Assert
    assert k.is_mac(strdata) is expected


def test_uuid_to_string():
    # Arrange
    k = Koan()
    u = [0] * 16

    # Act
    result = k.uuidToString(u)

    # Assert
    assert result == "00000000-0000-0000-0000-000000000000"


def test_random_uuid():
    # Arrange
    k = Koan()

    # Act
    result = k.randomUUID()

    # Assert
    assert len(result) == 16
    assert all(0 <= x <= 255 for x in result)


def test_get_uuid_returns_existing_value():
    # Arrange
    k = Koan()

    # Act
    result = k.get_uuid("existing-uuid")

    # Assert
    assert result == "existing-uuid"


def test_get_uuid_generates_random_when_falsy(mocker):
    # Arrange
    k = Koan()
    mocker.patch.object(k, "randomUUID", return_value=[0] * 16)

    # Act
    result = k.get_uuid(None)

    # Assert
    assert result == "00000000-0000-0000-0000-000000000000"


def test_merge_disk_data_reuses_last_size_and_driver():
    # Arrange
    k = Koan()
    paths = ["/a", "/b", "/c"]
    sizes = [10]
    drivers = ["raw", "qcow2"]

    # Act
    result = k.merge_disk_data(paths, sizes, drivers)

    # Assert
    assert result == [
        ["/a", 10, "raw"],
        ["/b", 10, "qcow2"],
        ["/c", 10, "qcow2"],
    ]


def test_merge_disk_data_no_paths_raises():
    # Arrange
    k = Koan()

    # Act / Assert
    with pytest.raises(InfoException, match="Disk configuration not resolvable"):
        k.merge_disk_data([], [], [])


def test_calc_virt_name_explicit_override():
    # Arrange
    k = Koan()
    k.virt_name = "my:vm name"

    # Act
    result = k.calc_virt_name({})

    # Assert
    assert result == "my_vm_name"


def test_calc_virt_name_uses_system_name_for_system_object():
    # Arrange
    k = Koan()
    k.virt_name = None
    profile_data = {"interfaces": {}, "name": "sys1"}

    # Act
    result = k.calc_virt_name(profile_data)

    # Assert
    assert result == "sys1"


def test_calc_virt_name_falls_back_to_time(mocker):
    # Arrange
    k = Koan()
    k.virt_name = None
    mocker.patch("koan.app.time.ctime", return_value="aa:bb cc")

    # Act
    result = k.calc_virt_name({})

    # Assert
    assert result == "aa_bb_cc"


@pytest.mark.parametrize(
    "override,data,expected",
    [
        (True, {}, True),
        (False, {"virt_auto_boot": "1"}, True),
        (False, {"virt_auto_boot": "true"}, True),
        (False, {"virt_auto_boot": "Y"}, True),
        (False, {"virt_auto_boot": "yes"}, True),
        (False, {"virt_auto_boot": "0"}, False),
        (False, {}, False),
    ],
)
def test_calc_virt_autoboot(override, data, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_autoboot(data, override)

    # Assert
    assert result is expected


@pytest.mark.parametrize(
    "override,data,expected",
    [
        (True, {}, True),
        (False, {"virt_pxe_boot": "1"}, True),
        (False, {"virt_pxe_boot": "yes"}, True),
        (False, {}, False),
        (False, {"virt_pxe_boot": "0"}, False),
    ],
)
def test_calc_virt_pxeboot(override, data, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_pxeboot(data, override)

    # Assert
    assert result is expected


def test_calc_virt_filesize_multiple_values():
    # Arrange
    k = Koan()
    data = {"virt_file_size": "5,10"}

    # Act
    result = k.calc_virt_filesize(data)

    # Assert
    assert result == [5, 10]


def test_calc_virt_filesize_default_when_missing():
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_filesize({})

    # Assert
    assert result == [0]


@pytest.mark.parametrize(
    "size,default_filesize,expected",
    [
        ("10", 1, 10),
        ("bogus", 5, 5),
        (None, 5, 5),
        ("", 5, 5),
    ],
)
def test_calc_virt_filesize2(size, default_filesize, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_filesize2({}, default_filesize=default_filesize, size=size)

    # Assert
    assert result == expected


def test_calc_virt_drivers_valid_and_invalid_mixed():
    # Arrange
    k = Koan()
    data = {"virt_disk_driver": "qcow2,bogus"}

    # Act
    result = k.calc_virt_drivers(data)

    # Assert
    assert result == ["qcow2", "raw"]


def test_calc_virt_drivers_default():
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_drivers({})

    # Assert
    assert result == ["raw"]


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"virt_ram": "128"}, 128),
        ({"virt_ram": "32"}, 64),
        ({}, 64),
    ],
)
def test_calc_virt_ram(data, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_ram(data)

    # Assert
    assert result == expected


def test_calc_virt_ram_non_numeric_string_raises():
    # Arrange
    # Note: this documents existing (arguably buggy) behavior - the method
    # catches a failed int() conversion but then re-runs int(size) in the
    # following `if`, which raises uncaught for non-numeric strings.
    k = Koan()

    # Act / Assert
    with pytest.raises(ValueError):
        k.calc_virt_ram({"virt_ram": "bogus"})


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"virt_cpus": "4"}, 4),
        ({"virt_cpus": "bogus"}, 1),
        ({}, 1),
    ],
)
def test_calc_virt_cpus(data, expected):
    # Arrange
    k = Koan()

    # Act
    result = k.calc_virt_cpus(data)

    # Assert
    assert result == expected


def test_calc_virt_mac_not_virt_returns_none():
    # Arrange
    k = Koan()
    k.is_virt = False
    k.system = "AA:BB:CC:DD:EE:FF"

    # Act
    result = k.calc_virt_mac({})

    # Assert
    assert result is None


def test_calc_virt_mac_system_is_mac():
    # Arrange
    k = Koan()
    k.is_virt = True
    k.system = "aa:bb:cc:dd:ee:ff"

    # Act
    result = k.calc_virt_mac({})

    # Assert
    assert result == "AA:BB:CC:DD:EE:FF"


def test_calc_virt_mac_generates_random(mocker):
    # Arrange
    k = Koan()
    k.is_virt = True
    k.system = "somesystem"
    mocker.patch("koan.app.utils.random_mac", return_value="00:50:56:11:22:33")

    # Act
    result = k.calc_virt_mac({})

    # Assert
    assert result == "00:50:56:11:22:33"


def test_calc_virt_uuid_always_none():
    # Arrange
    k = Koan()

    # Act / Assert
    # calc_virt_uuid has an unconditional `return None` before its body.
    assert k.calc_virt_uuid({"virt_uuid": "not-used"}) is None


def test_connect_fail_raises_with_server_and_port():
    # Arrange
    k = Koan()
    k.server = "myserver"
    k.port = 25151

    # Act / Assert
    with pytest.raises(
        InfoException, match="Could not communicate with myserver:25151"
    ):
        k.connect_fail()


def test_get_data_plural_calls_get_x():
    # Arrange
    k = Koan()
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_systems.return_value = [{"name": "a"}]

    # Act
    result = k.get_data("systems")

    # Assert
    assert result == [{"name": "a"}]
    k.xmlrpc_server.get_systems.assert_called_once_with()


def test_get_data_singular_calls_get_x_as_rendered():
    # Arrange
    k = Koan()
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_profile_as_rendered.return_value = {"name": "p1"}

    # Act
    result = k.get_data("profile", "p1")

    # Assert
    assert result == {"name": "p1"}
    k.xmlrpc_server.get_profile_as_rendered.assert_called_once_with("p1")


def test_get_data_empty_result_raises():
    # Arrange
    k = Koan()
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_systems.return_value = {}

    # Act / Assert
    with pytest.raises(InfoException, match="No entry/entries found"):
        k.get_data("systems")


def test_get_data_exception_calls_connect_fail():
    # Arrange
    k = Koan()
    k.server = "host"
    k.port = 1234
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_systems.side_effect = Exception("boom")

    # Act / Assert
    with pytest.raises(InfoException, match="Could not communicate with host:1234"):
        k.get_data("systems")


def test_list_invalid_what_raises():
    # Arrange
    k = Koan()

    # Act / Assert
    with pytest.raises(InfoException, match="koan does not know how to list that"):
        k.list("bogus")


def test_list_valid_prints_names(mocker, capsys):
    # Arrange
    k = Koan()
    mocker.patch.object(k, "get_data", return_value=[{"name": "p1"}, {"other": "x"}])

    # Act
    result = k.list("profiles")

    # Assert
    assert result is True
    captured = capsys.readouterr()
    assert "p1" in captured.out
    k.get_data.assert_called_once_with("profiles")


def test_display_prints_selected_params(mocker, capsys):
    # Arrange
    k = Koan()
    profile_data = {"name": "sys1", "distro": "d1", "kernel_options": "foo=bar"}

    def fake_net_install(after_download):
        after_download(k, profile_data)

    mocker.patch.object(k, "net_install", side_effect=fake_net_install)
    mocker.patch.object(k, "calc_kernel_args", return_value="foo=bar ")

    # Act
    k.display()

    # Assert
    captured = capsys.readouterr()
    assert "sys1" in captured.out
    assert "foo=bar" in captured.out
    k.calc_kernel_args.assert_called_once_with(profile_data)


def test_get_distro_files_server_set_builds_http_urls(mocker):
    # Arrange
    k = Koan()
    k.server = "myhost"
    mocker.patch("koan.app.os.chdir")
    mock_urlgrab = mocker.patch("koan.app.utils.urlgrab")
    profile_data = {
        "distro": "distro1",
        "kernel": "/var/lib/tftpboot/vmlinuz",
        "initrd": "/var/lib/tftpboot/initrd.img",
        "http_server": "myhost",
    }

    # Act
    k.get_distro_files(profile_data, "/boot")

    # Assert
    expected_initrd_url = "http://myhost/cobbler/images/distro1/initrd.img"
    expected_kernel_url = "http://myhost/cobbler/images/distro1/vmlinuz"
    assert mock_urlgrab.call_args_list == [
        call(expected_initrd_url, "/boot/initrd.img_koan"),
        call(expected_kernel_url, "/boot/vmlinuz_koan"),
    ]
    assert profile_data["kernel_local"] == "/boot/vmlinuz_koan"
    assert profile_data["initrd_local"] == "/boot/initrd.img_koan"


def test_get_distro_files_no_server_keeps_local_paths(mocker):
    # Arrange
    k = Koan()
    k.server = None
    mocker.patch("koan.app.os.chdir")
    mock_urlgrab = mocker.patch("koan.app.utils.urlgrab")
    profile_data = {
        "distro": "distro1",
        "kernel": "/local/vmlinuz",
        "initrd": "/local/initrd.img",
    }

    # Act
    k.get_distro_files(profile_data, "/boot")

    # Assert
    assert mock_urlgrab.call_args_list == [
        call("/local/initrd.img", "/boot/initrd.img_koan"),
        call("/local/vmlinuz", "/boot/vmlinuz_koan"),
    ]


def test_get_distro_files_download_error_wrapped(mocker):
    # Arrange
    k = Koan()
    k.server = None
    mocker.patch("koan.app.os.chdir")
    mocker.patch("koan.app.utils.urlgrab", side_effect=Exception("network error"))
    profile_data = {
        "distro": "distro1",
        "kernel": "/local/vmlinuz",
        "initrd": "/local/initrd.img",
    }

    # Act / Assert
    with pytest.raises(InfoException, match="error downloading files"):
        k.get_distro_files(profile_data, "/boot")


# ---------------------------------------------------------------------------
# GROUP 2 - calc_kernel_args
# ---------------------------------------------------------------------------


def test_calc_kernel_args_suse_breed():
    # Arrange
    k = Koan()
    pd = {
        "autoinst": "http://x/ks.cfg",
        "breed": "suse",
        "kernel_options": "",
        "os_version": "suse15",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "autoyast=http://x/ks.cfg "


def test_calc_kernel_args_debian_breed():
    # Arrange
    k = Koan()
    pd = {
        "autoinst": "http://x/preseed.cfg",
        "breed": "debian",
        "kernel_options": "",
        "os_version": "debian10",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "auto-install/enable=true priority=critical url=http://x/preseed.cfg "
    )


@pytest.mark.parametrize(
    "os_version,expected_prefix",
    [
        ("rhel6", "ks=http://x/ks.cfg "),
        ("rhel7", "inst.ks=http://x/ks.cfg "),
        ("fedora16", "ks=http://x/ks.cfg "),
        ("fedora17", "inst.ks=http://x/ks.cfg "),
    ],
)
def test_calc_kernel_args_redhat_family_ks_prefix(os_version, expected_prefix):
    # Arrange
    k = Koan()
    pd = {
        "autoinst": "http://x/ks.cfg",
        "breed": "redhat",
        "kernel_options": "",
        "os_version": os_version,
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == expected_prefix


def test_calc_kernel_args_appends_kernel_options():
    # Arrange
    k = Koan()
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "foo=bar baz",
        "os_version": "rhel7",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "foo=bar baz "


def test_calc_kernel_args_static_interface_redhat_non_newdracut():
    # Arrange
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "redhat",
        "kernel_options": "",
        "os_version": "rhel6",
        "interfaces": {
            "eth0": {
                "ip_address": "1.2.3.4",
                "netmask": "255.255.255.0",
                "dns_name": "host1",
            }
        },
        "gateway": "1.2.3.1",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "ksdevice=eth0 ip=1.2.3.4 netmask=255.255.255.0 gateway=1.2.3.1 "
        "dns=8.8.8.8,8.8.4.4 "
    )


def test_calc_kernel_args_static_interface_redhat_newdracut_rhel7():
    # Arrange
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "redhat",
        "kernel_options": "",
        "os_version": "rhel7",
        "interfaces": {
            "eth0": {
                "ip_address": "1.2.3.4",
                "netmask": "255.255.255.0",
                "dns_name": "host1",
            }
        },
        "gateway": "1.2.3.1",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "inst.ksdevice=eth0 ip=1.2.3.4::1.2.3.1:24:host1:eth0:none "
        "nameserver=8.8.8.8 "
    )


def test_calc_kernel_args_static_interface_redhat_newdracut_fedora():
    # Arrange
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "redhat",
        "kernel_options": "",
        "os_version": "fedora18",
        "interfaces": {
            "eth0": {
                "ip_address": "1.2.3.4",
                "netmask": "255.255.255.0",
                "dns_name": "host1",
            }
        },
        "gateway": "1.2.3.1",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "inst.ksdevice=eth0 " "ip=1.2.3.4::1.2.3.1:24:host1:eth0:none:8.8.8.8:8.8.4.4 "
    )


def test_calc_kernel_args_static_interface_debian():
    # Arrange
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "debian",
        "kernel_options": "",
        "os_version": "debian10",
        "interfaces": {
            "eth0": {
                "ip_address": "1.2.3.4",
                "netmask": "255.255.255.0",
                "dns_name": "host1",
            }
        },
        "gateway": "1.2.3.1",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
        "hostname": "host1.example.com",
        "name": "somename",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "hostname=host1 domain=example.com inst.ksdevice=eth0 "
        "netcfg/get_ipaddress=1.2.3.4 netcfg/get_netmask=255.255.255.0 "
        "netcfg/get_gateway=1.2.3.1 netcfg/get_nameservers=8.8.8.8 8.8.4.4 "
    )


def test_calc_kernel_args_static_interface_suse():
    # Arrange
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "suse",
        "kernel_options": "",
        "os_version": "suse15",
        "interfaces": {
            "eth0": {
                "ip_address": "1.2.3.4",
                "netmask": "255.255.255.0",
                "dns_name": "host1",
            }
        },
        "gateway": "1.2.3.1",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == (
        "netdevice=eth0 hostip=1.2.3.4 netmask=255.255.255.0 "
        "gateway=1.2.3.1 nameserver=8.8.8.8 "
    )


def test_calc_kernel_args_static_interface_eth_alternate_name_lookup():
    # Arrange
    # cobbler system interfaces are sometimes keyed by "intfX" instead of "ethX"
    k = Koan()
    k.static_interface = "eth0"
    pd = {
        "autoinst": None,
        "breed": "redhat",
        "kernel_options": "",
        "os_version": "rhel6",
        "interfaces": {
            "intf0": {
                "ip_address": "9.9.9.9",
                "netmask": "255.255.255.0",
                "dns_name": "h",
            }
        },
        "gateway": None,
        "name_servers": None,
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert "ip=9.9.9.9" in result
    assert "ksdevice=eth0" in result


def test_calc_kernel_args_static_interface_non_eth_direct_lookup():
    # Arrange
    k = Koan()
    k.static_interface = "bond0"
    pd = {
        "autoinst": None,
        "breed": "redhat",
        "kernel_options": "",
        "os_version": "rhel6",
        "interfaces": {
            "bond0": {
                "ip_address": "9.9.9.9",
                "netmask": "255.255.255.0",
                "dns_name": "h",
            }
        },
        "gateway": None,
        "name_servers": None,
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert "ip=9.9.9.9" in result
    assert "ksdevice=bond0" in result


def test_calc_kernel_args_kopts_override_adds_options():
    # Arrange
    k = Koan()
    k.kopts_override = "foo=bar baz=qux"
    pd = {"autoinst": None, "breed": None, "kernel_options": "", "os_version": "rhel7"}

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "foo=bar baz=qux "


def test_calc_kernel_args_kopts_override_overrides_existing_key():
    # Arrange
    k = Koan()
    k.kopts_override = "foo=new"
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "foo=old",
        "os_version": "rhel7",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "foo=new "


@pytest.mark.parametrize(
    "os_version,expected",
    [
        ("rhel6", "ks=file:ks.cfg "),
        ("rhel7", "inst.ks=file:ks.cfg "),
    ],
)
def test_calc_kernel_args_replace_self_embed_autoinst(os_version, expected):
    # Arrange
    k = Koan()
    k.embed_autoinst = True
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "",
        "os_version": os_version,
    }

    # Act
    result = k.calc_kernel_args(pd, replace_self=1)

    # Assert
    assert result == expected


def test_calc_kernel_args_replace_self_without_embed_autoinst_noop():
    # Arrange
    k = Koan()
    k.embed_autoinst = None
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "",
        "os_version": "rhel7",
    }

    # Act
    result = k.calc_kernel_args(pd, replace_self=1)

    # Assert
    assert result == ""


def test_calc_kernel_args_lang_fixup():
    # Arrange
    k = Koan()
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "lang",
        "os_version": "rhel7",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "lang= "


def test_calc_kernel_args_ksdevice_bootif_fixup():
    # Arrange
    k = Koan()
    pd = {
        "autoinst": None,
        "breed": None,
        "kernel_options": "ksdevice=bootif",
        "os_version": "rhel7",
    }

    # Act
    result = k.calc_kernel_args(pd)

    # Assert
    assert result == "ksdevice=link "


# ---------------------------------------------------------------------------
# GROUP 3 - run() validation / dispatch
# ---------------------------------------------------------------------------


def test_run_no_server_raises():
    # Arrange
    k = Koan()
    k.server = None

    # Act / Assert
    with pytest.raises(InfoException, match="no server specified"):
        k.run()


def test_run_no_action_selected_raises():
    # Arrange
    k = Koan()
    k.server = "host"

    # Act / Assert
    with pytest.raises(InfoException, match="choose: --virt"):
        k.run()


def test_run_multiple_actions_selected_raises():
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_virt = True
    k.is_display = True

    # Act / Assert
    with pytest.raises(InfoException, match="choose: --virt"):
        k.run()


def test_run_empty_server_with_profile_requires_server():
    # Arrange
    k = Koan()
    k.server = ""
    k.is_display = True
    k.profile = "p1"

    # Act / Assert
    with pytest.raises(InfoException, match="--server is required"):
        k.run()


def test_run_list_items_dispatches_to_list_and_returns(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.list_items = "profiles"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch.object(k, "list")

    # Act
    result = k.run()

    # Assert
    k.list.assert_called_once_with("profiles")
    assert result is None


def test_run_non_root_non_display_returns_3(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_update_files = True
    k.profile = "p1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=1000)
    mocker.patch.object(k, "update_files")

    # Act
    result = k.run()

    # Assert
    assert result == 3
    k.update_files.assert_not_called()


def test_run_non_root_is_virt_warns_but_continues(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_virt = True
    k.profile = "p1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=1000)
    mocker.patch.object(k, "virt")

    # Act
    k.run()

    # Assert
    k.virt.assert_called_once()


def test_run_non_root_is_display_continues(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=1000)
    mocker.patch.object(k, "display")

    # Act
    k.run()

    # Assert
    k.display.assert_called_once()


def test_run_is_virt_without_profile_system_image_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_virt = True
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(
        InfoException, match="must specify --profile, --system, or --image"
    ):
        k.run()


def test_run_autodetects_system_when_not_virt(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "autodetect_system", return_value="sys1")
    mocker.patch.object(k, "ask_profile")
    mocker.patch.object(k, "display")

    # Act
    k.run()

    # Assert
    assert k.system == "sys1"
    k.ask_profile.assert_not_called()
    k.display.assert_called_once()


def test_run_asks_profile_when_autodetect_fails(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "autodetect_system", return_value=None)
    mocker.patch.object(k, "ask_profile", return_value="prof1")
    mocker.patch.object(k, "display")

    # Act
    k.run()

    # Assert
    assert k.profile == "prof1"
    k.display.assert_called_once()


def test_run_invalid_virt_type_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    k.virt_type = "bogus"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(InfoException, match="--virt-type should be"):
        k.run()


def test_run_qemu_disk_type_without_qemu_virt_type_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    k.qemu_disk_type = "raw"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(
        InfoException, match="--qemu-disk-type must use with --virt-type=qemu"
    ):
        k.run()


def test_run_qemu_net_type_without_qemu_virt_type_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    k.qemu_net_type = "bridge"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(
        InfoException, match="--qemu-net-type must use with --virt-type=qemu"
    ):
        k.run()


def test_run_qemu_machine_type_without_qemu_virt_type_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    k.qemu_machine_type = "q35"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(
        InfoException, match="--qemu-machine-type must use with --virt-type=qemu"
    ):
        k.run()


def test_run_static_interface_with_profile_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.profile = "p1"
    k.static_interface = "eth0"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)

    # Act / Assert
    with pytest.raises(
        InfoException,
        match="--static-interface option is incompatible with --profile option",
    ):
        k.run()


def test_run_dispatches_to_virt(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_virt = True
    k.profile = "p1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "virt")

    # Act
    k.run()

    # Assert
    k.virt.assert_called_once()


def test_run_dispatches_to_kexec_replace_when_use_kexec(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_replace = True
    k.use_kexec = True
    k.system = "sys1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "kexec_replace")
    mocker.patch.object(k, "replace")

    # Act
    k.run()

    # Assert
    k.kexec_replace.assert_called_once()
    k.replace.assert_not_called()


def test_run_dispatches_to_replace_when_no_kexec(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_replace = True
    k.use_kexec = False
    k.system = "sys1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "kexec_replace")
    mocker.patch.object(k, "replace")

    # Act
    k.run()

    # Assert
    k.replace.assert_called_once()
    k.kexec_replace.assert_not_called()


def test_run_dispatches_to_update_files(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_update_files = True
    k.system = "sys1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "update_files")

    # Act
    k.run()

    # Assert
    k.update_files.assert_called_once()


def test_run_dispatches_to_update_config(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_update_config = True
    k.system = "sys1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "update_config")

    # Act
    k.run()

    # Assert
    k.update_config.assert_called_once()


def test_run_dispatches_to_display_by_default(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.is_display = True
    k.system = "sys1"
    mocker.patch("koan.app.utils.connect_to_server", return_value=MagicMock())
    mocker.patch("koan.app.os.getuid", return_value=0)
    mocker.patch.object(k, "display")

    # Act
    k.run()

    # Assert
    k.display.assert_called_once()


# ---------------------------------------------------------------------------
# GROUP 4 - moderate mocking
# ---------------------------------------------------------------------------


def test_ask_profile_returns_matching_choice(mocker):
    # Arrange
    k = Koan()
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_profiles.return_value = [{"name": "p1"}, {"name": "p2"}]
    mocker.patch("sys.stdin.readline", return_value="p2\n")

    # Act
    result = k.ask_profile()

    # Assert
    assert result == "p2"


def test_ask_profile_returns_none_when_no_match(mocker):
    # Arrange
    k = Koan()
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_profiles.return_value = [{"name": "p1"}, {"name": "p2"}]
    mocker.patch("sys.stdin.readline", return_value="unknown\n")

    # Act
    result = k.ask_profile()

    # Assert
    assert result is None


def test_ask_profile_connect_failure_raises(mocker):
    # Arrange
    k = Koan()
    k.server = "host"
    k.port = None
    k.xmlrpc_server = MagicMock()
    k.xmlrpc_server.get_profiles.side_effect = Exception("boom")

    # Act / Assert
    with pytest.raises(InfoException):
        k.ask_profile()


def test_autodetect_system_no_match_raises(mocker):
    # Arrange
    k = Koan()
    mocker.patch.object(
        k,
        "get_data",
        return_value=[
            {
                "name": "sysA",
                "interfaces": {
                    "eth0": {
                        "mac_address": "00:00:00:00:00:00",
                        "ip_address": "9.9.9.9",
                    }
                },
            }
        ],
    )
    mocker.patch(
        "koan.app.utils.get_network_info",
        return_value={
            "eth0": {"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "1.2.3.4"}
        },
    )

    # Act / Assert
    with pytest.raises(InfoException, match="Could not find a matching system"):
        k.autodetect_system()


def test_autodetect_system_no_match_interactive_returns_none(mocker):
    # Arrange
    k = Koan()
    mocker.patch.object(
        k,
        "get_data",
        return_value=[
            {
                "name": "sysA",
                "interfaces": {
                    "eth0": {
                        "mac_address": "00:00:00:00:00:00",
                        "ip_address": "9.9.9.9",
                    }
                },
            }
        ],
    )
    mocker.patch(
        "koan.app.utils.get_network_info",
        return_value={
            "eth0": {"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "1.2.3.4"}
        },
    )

    # Act
    result = k.autodetect_system(allow_interactive=True)

    # Assert
    assert result is None


def test_autodetect_system_single_match_by_mac(mocker):
    # Arrange
    k = Koan()
    mocker.patch.object(
        k,
        "get_data",
        return_value=[
            {
                "name": "sysA",
                "interfaces": {
                    "eth0": {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "ip_address": "9.9.9.9",
                    }
                },
            }
        ],
    )
    mocker.patch(
        "koan.app.utils.get_network_info",
        return_value={
            "eth0": {"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "1.2.3.4"}
        },
    )

    # Act
    result = k.autodetect_system()

    # Assert
    assert result == "sysA"


def test_autodetect_system_multiple_matches_raises(mocker):
    # Arrange
    k = Koan()
    mocker.patch.object(
        k,
        "get_data",
        return_value=[
            {
                "name": "sysA",
                "interfaces": {
                    "eth0": {
                        "mac_address": "AA:BB:CC:DD:EE:FF",
                        "ip_address": "9.9.9.9",
                    }
                },
            },
            {
                "name": "sysB",
                "interfaces": {
                    "eth0": {
                        "mac_address": "11:22:33:44:55:66",
                        "ip_address": "1.2.3.4",
                    }
                },
            },
        ],
    )
    mocker.patch(
        "koan.app.utils.get_network_info",
        return_value={
            "eth0": {"mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "1.2.3.4"}
        },
    )

    # Act / Assert
    with pytest.raises(InfoException, match="Error: Multiple systems matched"):
        k.autodetect_system()


def test_virt_choose_virt_clone_image():
    # Arrange
    from koan.virt import image

    k = Koan()
    k.image = "myimage"
    pd = {"image_type": "virt-clone"}

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose(pd)

    # Assert
    assert creator is image.start_install
    assert fullvirt is True
    assert uuid is None
    assert can_poll is None


def test_virt_choose_xenpv():
    # Arrange
    from koan.virt import xen

    k = Koan()
    k.image = None
    k.virt_type = "xenpv"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is xen.start_install
    assert fullvirt is False
    assert can_poll == "xen"
    assert uuid is not None


def test_virt_choose_xenfv():
    # Arrange
    from koan.virt import xen

    k = Koan()
    k.image = None
    k.virt_type = "xenfv"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is xen.start_install
    assert fullvirt is True
    assert can_poll == "xen"


def test_virt_choose_qemu():
    # Arrange
    from koan.virt import qemu

    k = Koan()
    k.image = None
    k.virt_type = "qemu"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is qemu.start_install
    assert fullvirt is True
    assert uuid is None
    assert can_poll == "qemu"


def test_virt_choose_kvm():
    # Arrange
    from koan.virt import qemu

    k = Koan()
    k.image = None
    k.virt_type = "kvm"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is qemu.start_install
    assert fullvirt is True
    assert can_poll == "qemu"


def test_virt_choose_vmware():
    # Arrange
    from koan.virt import vmw

    k = Koan()
    k.image = None
    k.virt_type = "vmware"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is vmw.start_install
    assert uuid is None
    assert fullvirt is False
    assert can_poll is None


def test_virt_choose_openvz():
    # Arrange
    from koan.virt import openvz

    k = Koan()
    k.image = None
    k.virt_type = "openvz"

    # Act
    uuid, creator, fullvirt, can_poll = k.virt_choose({})

    # Assert
    assert creator is openvz.start_install
    assert uuid is None


def test_virt_choose_invalid_type_raises():
    # Arrange
    k = Koan()
    k.image = None
    k.virt_type = "bogus"

    # Act / Assert
    with pytest.raises(InfoException, match="Unspecified virt type: bogus"):
        k.virt_choose({})


def test_get_install_tree_from_profile_data_remote_url(capsys):
    # Arrange
    k = Koan()
    profile_data = {
        "autoinstall_meta": {"tree": "http://otherhost/tree"},
        "http_server": "myhost",
    }

    # Act
    k.get_install_tree_from_profile_data(profile_data)

    # Assert
    assert profile_data["install_tree"] == "http://otherhost/tree"


def test_get_install_tree_from_profile_data_local_path():
    # Arrange
    k = Koan()
    profile_data = {
        "autoinstall_meta": {"tree": "/path/to/tree"},
        "http_server": "myhost",
    }

    # Act
    k.get_install_tree_from_profile_data(profile_data)

    # Assert
    assert profile_data["install_tree"] == "http://myhost/path/to/tree"


def test_get_install_tree_from_profile_data_suse_fallback_to_kernel_options():
    # Arrange
    k = Koan()
    profile_data = {
        "breed": "suse",
        "kernel_options": "foo=bar install=http://x/tree bar=baz",
    }

    # Act
    k.get_install_tree_from_profile_data(profile_data)

    # Assert
    assert profile_data["install_tree"] == "http://x/tree"


def test_get_install_tree_from_profile_data_non_suse_exception_is_swallowed():
    # Arrange
    k = Koan()
    profile_data = {"breed": "redhat"}

    # Act
    k.get_install_tree_from_profile_data(profile_data)

    # Assert
    assert "install_tree" not in profile_data
