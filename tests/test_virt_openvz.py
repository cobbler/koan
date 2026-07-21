import os

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


def test_happy_path_calls_os_system_twice_and_installs_container_tree(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0])
    mock_install = mocker.patch("koan.virt.openvz._install_container_tree")

    result = openvz.start_install(**_base_kwargs())

    assert result is None
    assert mock_system.call_count == 2

    commands = [call.args[0] for call in mock_system.call_args_list]
    assert "vzcfgvalidate" in commands[0]
    assert "/etc/vz/conf/101.conf" in commands[0]
    assert "vzctl start 101" in commands[1]

    mock_install.assert_called_once_with(
        "testvm", "http://server.example.com/autoinst.ks", "/vz/private/101"
    )

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
    mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0])
    mocker.patch("koan.virt.openvz._install_container_tree")

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
    mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 0])
    mocker.patch("koan.virt.openvz._install_container_tree")

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
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0])
    mocker.patch(
        "koan.virt.openvz._install_container_tree",
        side_effect=RuntimeError("boom"),
    )

    with pytest.raises(OVZCreateException, match=r"Container creation 101 failed"):
        openvz.start_install(**_base_kwargs())

    assert mock_system.call_count == 1


def test_start_container_failure_raises(mocker):
    mocker.patch("koan.virt.openvz.os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open())
    mock_system = mocker.patch("koan.virt.openvz.os.system", side_effect=[0, 1])
    mocker.patch("koan.virt.openvz._install_container_tree")

    with pytest.raises(OVZCreateException, match=r"Start container 101 failed"):
        openvz.start_install(**_base_kwargs())

    assert mock_system.call_count == 2


def test_extract_rootpw_returns_last_field_of_rootpw_line():
    kickstart = "lang en_US\nrootpw --iscrypted $6$abcdef$somehash\nreboot\n"

    assert openvz._extract_rootpw(kickstart) == "$6$abcdef$somehash"


def test_extract_rootpw_returns_none_when_absent():
    kickstart = "lang en_US\nreboot\n"

    assert openvz._extract_rootpw(kickstart) is None


@pytest.mark.parametrize(
    "kickstart,expected",
    [
        ("%post --interpreter /usr/bin/python3\necho hi\n", "/usr/bin/python3"),
        ("%post\necho hi\n", "/bin/sh"),
        ("lang en_US\n", "/bin/sh"),
    ],
)
def test_extract_post_install_interpreter(kickstart, expected):
    assert openvz._extract_post_install_interpreter(kickstart) == expected


def test_extract_post_install_script_returns_text_after_post_line():
    kickstart = "lang en_US\n%post\necho hi\necho done\n"

    assert openvz._extract_post_install_script(kickstart) == "echo hi\necho done"


def test_extract_post_install_script_returns_empty_when_no_post_section():
    kickstart = "lang en_US\nreboot\n"

    assert openvz._extract_post_install_script(kickstart) == ""


def test_extract_services_returns_enabled_and_disabled_lists():
    kickstart = "services --disabled=sendmail,cups --enabled=sshd,network\n"

    enabled, disabled = openvz._extract_services(kickstart)

    assert enabled == ["sshd", "network"]
    assert disabled == ["sendmail", "cups"]


def test_extract_services_returns_empty_lists_when_absent():
    kickstart = "lang en_US\n"

    enabled, disabled = openvz._extract_services(kickstart)

    assert enabled == []
    assert disabled == []


def test_extract_base_repo_url_returns_url_value():
    kickstart = "url --url=http://mirror.example.com/os/x86_64\n"

    assert (
        openvz._extract_base_repo_url(kickstart)
        == "http://mirror.example.com/os/x86_64"
    )


def test_extract_base_repo_url_returns_none_when_absent():
    kickstart = "lang en_US\n"

    assert openvz._extract_base_repo_url(kickstart) is None


@pytest.mark.parametrize(
    "kickstart,expected",
    [
        ("url --url=http://x --ignoremissing\n", True),
        ("url --url=http://x\n", False),
    ],
)
def test_extract_ignoremissing(kickstart, expected):
    assert openvz._extract_ignoremissing(kickstart) == expected


@pytest.mark.parametrize(
    "kickstart,expected",
    [
        ("%packages --nobase\n@core\n%post\n", True),
        ("%packages\n@core\n%post\n", False),
    ],
)
def test_extract_nobase(kickstart, expected):
    assert openvz._extract_nobase(kickstart) == expected


def test_extract_repos_parses_name_and_baseurl():
    kickstart = (
        "repo --name=epel --baseurl=http://example.com/epel\n"
        "repo --name=extras --baseurl=http://example.com/extras\n"
    )

    repos = openvz._extract_repos(kickstart)

    assert repos == [
        ("epel", "name=epel", "baseurl=http://example.com/epel"),
        ("extras", "name=extras", "baseurl=http://example.com/extras"),
    ]


def test_extract_repos_returns_empty_list_when_absent():
    assert openvz._extract_repos("lang en_US\n") == []


def test_extract_repos_ignores_lines_not_starting_with_repo_token():
    # "repository" starts with the substring "repo" but is not the "repo" directive
    kickstart = "repository-note this is not a repo line\n"

    assert openvz._extract_repos(kickstart) == []


def test_extract_repos_ignores_bare_repo_line_without_directives():
    assert openvz._extract_repos("repo\n") == []


def test_extract_packages_parses_install_remove_and_group_entries():
    kickstart = (
        "%packages --nobase\n"
        "@core\n"
        "vim-enhanced\n"
        "-sendmail\n"
        "-@auto-fedora\n"
        "%post\n"
        "echo hi\n"
    )

    packages = openvz._extract_packages(kickstart)

    assert packages == [
        ("install", True, "core"),
        ("install", False, "vim-enhanced"),
        ("remove", False, "sendmail"),
        ("remove", True, "auto-fedora"),
    ]


def test_extract_packages_skips_blank_and_comment_lines():
    kickstart = "%packages\n\n# a comment\nvim-enhanced\n%post\n"

    assert openvz._extract_packages(kickstart) == [("install", False, "vim-enhanced")]


def test_extract_packages_returns_empty_list_when_no_packages_section():
    assert openvz._extract_packages("lang en_US\n") == []


def test_extract_packages_reads_to_end_of_file_when_no_post_section():
    kickstart = "%packages\nvim-enhanced\n"

    assert openvz._extract_packages(kickstart) == [("install", False, "vim-enhanced")]


def test_build_yum_config_includes_base_repo_and_main_section():
    config = openvz._build_yum_config(
        base_repo_url="http://mirror.example.com/os", ignore_missing=False, repos=[]
    )

    assert "[main]" in config
    assert "[base-os]" in config
    assert "baseurl=http://mirror.example.com/os" in config
    assert "skip_broken=1" not in config


def test_build_yum_config_sets_skip_broken_when_ignore_missing():
    config = openvz._build_yum_config(
        base_repo_url="http://mirror.example.com/os", ignore_missing=True, repos=[]
    )

    assert "skip_broken=1" in config


def test_build_yum_config_includes_additional_repo_sections():
    config = openvz._build_yum_config(
        base_repo_url="http://mirror.example.com/os",
        ignore_missing=False,
        repos=[("epel", "name=epel", "baseurl=http://example.com/epel")],
    )

    assert "[epel]" in config
    assert "name=epel" in config
    assert "baseurl=http://example.com/epel" in config


def test_build_yum_script_includes_extra_packages_and_exclusions():
    script = openvz._build_yum_script(packages=[], nobase=False)

    assert "config assumeyes True" in script
    assert "config gpgcheck False" in script
    assert "install vim-minimal ssh-clients openssh-server logrotate" in script
    assert 'config exclude "selinux-policy-targeted kernel* *firmware* b43*"' in script
    assert script.strip().endswith("run")
    assert "groupremove base" not in script


def test_build_yum_script_translates_package_actions():
    packages = [
        ("install", True, "core"),
        ("install", False, "vim-enhanced"),
        ("remove", False, "sendmail"),
        ("remove", True, "auto-fedora"),
    ]

    script = openvz._build_yum_script(packages=packages, nobase=False)

    assert 'groupinstall "core"' in script
    assert 'install "vim-enhanced"' in script
    assert 'remove "sendmail"' in script
    assert 'groupremove "auto-fedora"' in script


def test_build_yum_script_adds_groupremove_base_when_nobase():
    script = openvz._build_yum_script(packages=[], nobase=True)

    lines = script.splitlines()
    assert lines.index("groupremove base") < lines.index("run")


def test_run_yum_install_installs_then_removes_kernel_packages(mocker):
    mock_call = mocker.patch("koan.virt.openvz.utils.subprocess_call")

    openvz._run_yum_install("/vz/private/101", "/tmp/x-yum.cfg", "/tmp/x-yum.yum")

    assert mock_call.call_count == 2
    install_cmd = mock_call.call_args_list[0].args[0]
    assert "yum" in install_cmd
    assert "shell" in install_cmd
    assert "--config=/tmp/x-yum.cfg" in install_cmd
    assert "--installroot=/vz/private/101" in install_cmd
    assert "/tmp/x-yum.yum" in install_cmd

    remove_cmd = mock_call.call_args_list[1].args[0]
    assert "remove" in remove_cmd
    assert "kernel" in remove_cmd
    assert "--installroot=/vz/private/101" in remove_cmd


def test_apply_services_script_writes_disabled_then_enabled_and_chroots(mocker):
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_move = mocker.patch("koan.virt.openvz.shutil.move")
    mock_call = mocker.patch("koan.virt.openvz.utils.subprocess_call")

    openvz._apply_services_script(
        "/vz/private/101", "testvm", enabled=["sshd"], disabled=["sendmail"]
    )

    mock_open.assert_called_once_with("/tmp/testvm-services.sh", "w")
    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    disabled_index = written.index("chkconfig --level 345 sendmail off")
    enabled_index = written.index("chkconfig --level 345 sshd on")
    assert disabled_index < enabled_index

    mock_move.assert_called_once_with(
        "/tmp/testvm-services.sh", "/vz/private/101/tmp/testvm-services.sh"
    )
    mock_call.assert_called_once_with(
        ["chroot", "/vz/private/101", "/bin/bash", "/tmp/testvm-services.sh"],
        ignore_rc=True,
    )


def test_apply_post_install_script_writes_body_and_chroots(mocker):
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_move = mocker.patch("koan.virt.openvz.shutil.move")
    mock_call = mocker.patch("koan.virt.openvz.utils.subprocess_call")

    openvz._apply_post_install_script(
        "/vz/private/101", "testvm", "/usr/bin/python3", "echo hi"
    )

    mock_open.assert_called_once_with("/tmp/testvm-post-install", "w")
    mock_open().write.assert_called_once_with("echo hi")

    mock_move.assert_called_once_with(
        "/tmp/testvm-post-install", "/vz/private/101/tmp/testvm-post-install"
    )
    mock_call.assert_called_once_with(
        ["chroot", "/vz/private/101", "/usr/bin/python3", "/tmp/testvm-post-install"],
        ignore_rc=True,
    )


def test_tune_container_tree_applies_expected_filesystem_changes(mocker, tmp_path):
    rootdir = tmp_path / "rootdir"
    for relative_dir in (
        "etc/init",
        "etc/ssh",
        "dev",
        "etc/udev/devices",
        "tmp",
        "var/tmp",
    ):
        (rootdir / relative_dir).mkdir(parents=True)

    (rootdir / "etc/init/rc.conf").write_text("console output here\nother line\n")
    (rootdir / "etc/init/control-alt-delete.conf").write_text("stop\n")
    (rootdir / "etc/ssh/sshd_config").write_text("GSSAPIAuthentication yes\n")
    (rootdir / "etc/shadow").write_text("root:x:19000:0:99999:7:::\n")
    (rootdir / "dev/null").write_text("")

    mock_call = mocker.patch("koan.virt.openvz.utils.subprocess_call")

    openvz._tune_container_tree(str(rootdir), "$6$hashedpw$")

    assert (rootdir / "etc/init/rc.conf").read_text().startswith("#console")
    assert not (rootdir / "etc/init/control-alt-delete.conf").exists()
    assert "GSSAPIAuthentication no" in (rootdir / "etc/ssh/sshd_config").read_text()
    assert (rootdir / "etc/selinux/config").read_text() == "SELINUX=disabled\n"
    assert "root:$6$hashedpw$:" in (rootdir / "etc/shadow").read_text()
    assert os.path.islink(rootdir / "etc/mtab")
    assert os.readlink(rootdir / "etc/mtab") == "/proc/mounts"
    assert not (rootdir / "dev/null").exists()
    assert os.path.islink(rootdir / "dev/fd")
    assert os.path.islink(rootdir / "etc/udev/devices/fd")
    assert oct(os.stat(rootdir / "tmp").st_mode)[-4:] == "1777"
    assert oct(os.stat(rootdir / "var/tmp").st_mode)[-4:] == "1777"

    makedev_dirs = [call.args[0][2] for call in mock_call.call_args_list]
    assert str(rootdir / "dev") in makedev_dirs
    assert str(rootdir / "etc/udev/devices") in makedev_dirs


_SAMPLE_KICKSTART = (
    "rootpw --iscrypted $6$hash\n"
    "url --url=http://mirror.example.com/os\n"
    "services --enabled=sshd --disabled=sendmail\n"
    "%packages\n"
    "@core\n"
    "%post --interpreter /bin/sh\n"
    "echo hi\n"
)


def test_install_container_tree_orchestrates_steps_in_order(mocker):
    mocker.patch("koan.virt.openvz.utils.urlread", return_value=_SAMPLE_KICKSTART)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch(
        "koan.virt.openvz.glob.glob",
        return_value=["/vz/private/101/etc/yum.repos.d/base.repo"],
    )
    mock_remove = mocker.patch("koan.virt.openvz.os.remove")
    mock_run_yum = mocker.patch("koan.virt.openvz._run_yum_install")
    mock_services = mocker.patch("koan.virt.openvz._apply_services_script")
    mock_post = mocker.patch("koan.virt.openvz._apply_post_install_script")
    mock_tune = mocker.patch("koan.virt.openvz._tune_container_tree")

    openvz._install_container_tree(
        "testvm", "http://server.example.com/ks.cfg", "/vz/private/101"
    )

    mock_open.assert_any_call("/tmp/testvm-yum.cfg", "w")
    mock_open.assert_any_call("/tmp/testvm-yum.yum", "w")
    mock_run_yum.assert_called_once_with(
        "/vz/private/101", "/tmp/testvm-yum.cfg", "/tmp/testvm-yum.yum"
    )
    mock_remove.assert_called_once_with("/vz/private/101/etc/yum.repos.d/base.repo")
    mock_services.assert_called_once_with(
        "/vz/private/101", "testvm", ["sshd"], ["sendmail"]
    )
    mock_post.assert_called_once_with("/vz/private/101", "testvm", "/bin/sh", "echo hi")
    mock_tune.assert_called_once_with("/vz/private/101", "$6$hash")


def test_disable_gssapi_authentication_noop_when_file_missing(tmp_path):
    missing_path = str(tmp_path / "does-not-exist")

    openvz._disable_gssapi_authentication(missing_path)

    assert not os.path.exists(missing_path)


def test_set_root_password_hash_noop_when_file_missing(tmp_path):
    missing_path = str(tmp_path / "does-not-exist")

    openvz._set_root_password_hash(missing_path, "$6$hash")

    assert not os.path.exists(missing_path)


def test_set_root_password_hash_noop_when_rootpw_falsy(tmp_path):
    shadow_path = tmp_path / "shadow"
    shadow_path.write_text("root:x:19000:0:99999:7:::\n")

    openvz._set_root_password_hash(str(shadow_path), None)

    assert shadow_path.read_text() == "root:x:19000:0:99999:7:::\n"


def test_replace_symlink_removes_pre_existing_link(tmp_path):
    link_path = tmp_path / "mtab"
    link_path.symlink_to("/some/stale/target")

    openvz._replace_symlink(str(link_path), "/proc/mounts")

    assert os.readlink(link_path) == "/proc/mounts"


def test_install_container_tree_decodes_bytes_kickstart(mocker):
    mocker.patch(
        "koan.virt.openvz.utils.urlread",
        return_value=_SAMPLE_KICKSTART.encode(),
    )
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("koan.virt.openvz.glob.glob", return_value=[])
    mocker.patch("koan.virt.openvz._run_yum_install")
    mocker.patch("koan.virt.openvz._apply_services_script")
    mocker.patch("koan.virt.openvz._apply_post_install_script")
    mock_tune = mocker.patch("koan.virt.openvz._tune_container_tree")

    openvz._install_container_tree(
        "testvm", "http://server.example.com/ks.cfg", "/vz/private/101"
    )

    mock_tune.assert_called_once_with("/vz/private/101", "$6$hash")
