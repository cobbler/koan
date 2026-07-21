import pytest

from koan.cexceptions import OVZCreateException
from koan.virt import openvz

VZCFGVALIDATE = "/usr/sbin/vzcfgvalidate"
VZCTL = "/usr/sbin/vzctl"


def _base_kwargs(autoinstall_meta=None, virt_auto_boot="1"):
    if autoinstall_meta is None:
        autoinstall_meta = [("vz_ctid", "101")]
    return {
        "name": "testvm",
        "profile_data": {
            "autoinst": "http://server.example.com/autoinst.ks",
            "breed": "redhat",
            "hostname": "test-host",
            "ip_address_eth0": "192.168.1.10",
            "name_servers": ["8.8.8.8", "8.8.4.4"],
            "virt_file_size": "10",
            "virt_ram": "512",
            "virt_cpus": "2",
            "virt_auto_boot": virt_auto_boot,
            "autoinstall_meta": autoinstall_meta,
        },
    }


@pytest.mark.parametrize(
    "exists_side_effect",
    [
        # neither tool present
        lambda path: False,
        # only vzcfgvalidate present
        lambda path: path == VZCFGVALIDATE,
        # only vzctl present
        lambda path: path == VZCTL,
    ],
)
def test_missing_tools_raises(exists_side_effect, mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", side_effect=exists_side_effect)

    with pytest.raises(
        OVZCreateException,
        match=r"Cannot find /usr/sbin/vzcfgvalidate and/or /usr/sbin/vzctl! "
        r"Are OpenVZ tools installed\?",
    ):
        openvz.start_install(**_base_kwargs())


def test_missing_vz_ctid_raises(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)

    with pytest.raises(
        OVZCreateException,
        match=r'Mandatory "vz_ctid" parameter not found in autoinstall_meta!',
    ):
        openvz.start_install(**_base_kwargs(autoinstall_meta=[]))


def test_invalid_ctid_returns_1_and_prints_message(mocker, capsys):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)

    result = openvz.start_install(
        **_base_kwargs(autoinstall_meta=[("vz_ctid", "not-a-number")])
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "Invalid CTID in autoinstall_meta. Exiting..." in captured.out


def test_happy_path_calls_os_system_three_times_with_expected_commands(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0, 0])

    result = openvz.start_install(**_base_kwargs())

    assert result is None
    assert mock_system.call_count == 3

    commands = [call.args[0] for call in mock_system.call_args_list]
    assert "vzcfgvalidate" in commands[0]
    assert "/etc/vz/conf/101.conf" in commands[0]
    assert "ovz-install" in commands[1]
    assert "testvm" in commands[1]
    assert "http://server.example.com/autoinst.ks" in commands[1]
    assert "/vz/private/101" in commands[1]
    assert "vzctl start 101" in commands[2]

    mock_open.assert_called_once_with("/etc/vz/conf/101.conf", "w+")
    handle = mock_open()
    handle.close.assert_called_once()


@pytest.mark.parametrize("virt_auto_boot", ["1", 1, True, "0", 0, False, ""])
def test_onboot_not_written_to_config_by_default(virt_auto_boot, mocker):
    # ONBOOT is not part of the minimal config and virt_auto_boot is never
    # merged into it unless explicitly provided via autoinstall_meta's
    # "vz_onboot" key, so it should never show up in the written config
    # regardless of virt_auto_boot's value.
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0, 0])

    openvz.start_install(**_base_kwargs(virt_auto_boot=virt_auto_boot))

    handle = mock_open()
    written_keys = [
        call.args[0].split("=", 1)[0] for call in handle.write.call_args_list
    ]
    assert "ONBOOT" not in written_keys


def test_onboot_override_from_autoinstall_meta(mocker):
    # When "vz_onboot" is provided via autoinstall_meta, its raw value is
    # written verbatim into the config -- it is not affected by the
    # virt_auto_boot-derived yes/no mapping.
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0, 0])

    openvz.start_install(
        **_base_kwargs(
            autoinstall_meta=[("vz_ctid", "101"), ("vz_onboot", "no")],
            virt_auto_boot="1",
        )
    )

    handle = mock_open()
    written = [call.args[0] for call in handle.write.call_args_list]
    assert 'ONBOOT="no"\n' in written


def test_validate_config_failure_raises(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[1])

    with pytest.raises(
        OVZCreateException, match=r"Container 101 config file is not valid"
    ):
        openvz.start_install(**_base_kwargs())

    assert mock_system.call_count == 1


def test_container_creation_failure_raises(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 1])

    with pytest.raises(OVZCreateException, match=r"Container creation 101 failed"):
        openvz.start_install(**_base_kwargs())

    assert mock_system.call_count == 2


def test_start_container_failure_raises(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0, 1])

    with pytest.raises(OVZCreateException, match=r"Start container 101 failed"):
        openvz.start_install(**_base_kwargs())

    assert mock_system.call_count == 3
