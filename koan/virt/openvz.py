"""
OpenVZ container-type virtualization installation functions.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2012 Artem Kanarev <kanarev AT tncc.ru>, Sergey Podushkin <psv AT tncc.ru>

import glob
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from koan import utils
from koan.cexceptions import OVZCreateException


def _extract_rootpw(kickstart_text: str) -> Optional[str]:
    """
    Extract the root password hash/value from a "rootpw ..." kickstart line.
    """
    for line in kickstart_text.splitlines():
        if line.startswith("rootpw"):
            fields = line.split()
            if len(fields) > 1:
                return fields[-1]
    return None


def _extract_post_install_interpreter(kickstart_text: str) -> str:
    """
    Extract the interpreter from "%post --interpreter <shell>", defaulting to /bin/sh.
    """
    for line in kickstart_text.splitlines():
        if line.startswith("%post"):
            match = re.search(r"--interpreter\s+(\S+)", line)
            if match:
                return match.group(1)
            break
    return "/bin/sh"


def _extract_post_install_script(kickstart_text: str) -> str:
    """
    Return everything after the first "%post" line, as the post-install script body.
    """
    lines = kickstart_text.splitlines()
    for index, line in enumerate(lines):
        if "%post" in line:
            return "\n".join(lines[index + 1 :])
    return ""


def _extract_services(kickstart_text: str) -> Tuple[List[str], List[str]]:
    """
    Extract enabled/disabled service lists from a "services --enabled=... --disabled=..." line.
    """
    enabled: List[str] = []
    disabled: List[str] = []
    for line in kickstart_text.splitlines():
        if not line.startswith("services"):
            continue
        enabled_match = re.search(r"--enabled[= ](\S+)", line)
        if enabled_match:
            enabled = enabled_match.group(1).split(",")
        disabled_match = re.search(r"--disabled[= ](\S+)", line)
        if disabled_match:
            disabled = disabled_match.group(1).split(",")
        break
    return enabled, disabled


def _extract_base_repo_url(kickstart_text: str) -> Optional[str]:
    """
    Extract the base install tree URL from a "url --url=..." line.
    """
    for line in kickstart_text.splitlines():
        if line.startswith("url"):
            match = re.search(r"--url[= ](\S+)", line)
            if match:
                return match.group(1)
    return None


def _extract_ignoremissing(kickstart_text: str) -> bool:
    return "--ignoremissing" in kickstart_text


def _extract_nobase(kickstart_text: str) -> bool:
    return "--nobase" in kickstart_text


def _extract_repos(kickstart_text: str) -> List[Tuple[str, str, str]]:
    """
    Extract additional yum repos from "repo --name=... --baseurl=..." lines.

    Returns a list of (tag, name_directive, rest_directive) tuples, where
    name_directive/rest_directive are the raw "key=value" tokens intended to be
    written verbatim into a yum repo config file.
    """
    repos: List[Tuple[str, str, str]] = []
    for line in kickstart_text.splitlines():
        tokens = line.split()
        if not tokens or tokens[0] != "repo":
            continue
        directive_tokens = [token.replace("--", "") for token in tokens[1:]]
        if not directive_tokens:
            continue
        name_directive = directive_tokens[0]
        rest_directive = " ".join(directive_tokens[1:])
        tag = name_directive.split("=", 1)[-1]
        repos.append((tag, name_directive, rest_directive))
    return repos


def _extract_packages(kickstart_text: str) -> List[Tuple[str, bool, str]]:
    """
    Extract package/group install-or-remove entries from the "%packages" section.

    Returns a list of (action, is_group, name) tuples where action is
    "install" or "remove".
    """
    lines = kickstart_text.splitlines()
    start_index: Optional[int] = None
    for index, line in enumerate(lines):
        if line.strip().startswith("%packages"):
            start_index = index + 1
            break
    if start_index is None:
        return []

    end_index = len(lines)
    for index in range(start_index, len(lines)):
        if lines[index].strip().startswith("%post"):
            end_index = index
            break

    packages: List[Tuple[str, bool, str]] = []
    for line in lines[start_index:end_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("%"):
            continue
        action = "install"
        if stripped.startswith("-"):
            action = "remove"
            stripped = stripped[1:]
        is_group = False
        if stripped.startswith("@"):
            is_group = True
            stripped = stripped[1:]
        packages.append((action, is_group, stripped))
    return packages


# packages we don't need to install (but included in installed groups)
_EXCLUDED_PACKAGES = "selinux-policy-targeted kernel* *firmware* b43*"

# packages we want installed, besides of those listed in the kickstart
_EXTRA_PACKAGES = "vim-minimal ssh-clients openssh-server logrotate"


def _build_yum_config(
    base_repo_url: Optional[str],
    ignore_missing: bool,
    repos: List[Tuple[str, str, str]],
) -> str:
    """
    Build the contents of a temporary yum config restricted to the base install
    tree repo plus any additional repos declared in the kickstart file.
    """
    lines = [
        "[main]",
        r"cachedir=/var/cache/yum/$basearch/$releasever",
        "keepcache=0",
        "debuglevel=2",
        "logfile=/var/log/yum.log",
        "exactarch=1",
        "obsoletes=1",
        "gpgcheck=0",
        "plugins=1",
        "distroverpkg=centos-release",
        "reposdir=/dev/null",
        "groupremove_leaf_only=1",
        "group_package_types=mandatory",
        "tsflags=nodocs",
    ]
    if ignore_missing:
        lines.append("skip_broken=1")

    lines.extend(
        [
            "",
            "[base-os]",
            "name=base-os",
            "baseurl=%s" % base_repo_url,
            "enabled=1",
            "priority=1",
            "gpgcheck=0",
        ]
    )

    for tag, name_directive, rest_directive in repos:
        lines.extend(
            [
                "",
                "[%s]" % tag,
                name_directive,
                rest_directive,
                "enabled=1",
                "priority=99",
                "gpgcheck=0",
            ]
        )

    return "\n".join(lines) + "\n"


def _build_yum_script(packages: List[Tuple[str, bool, str]], nobase: bool) -> str:
    """
    Build a "yum shell" script installing/removing the given packages/groups.
    """
    lines = [
        "config assumeyes True",
        "config gpgcheck False",
        "install %s" % _EXTRA_PACKAGES,
        'config exclude "%s"' % _EXCLUDED_PACKAGES,
    ]
    for action, is_group, name in packages:
        prefix = ("group" if is_group else "") + action
        lines.append('%s "%s"' % (prefix, name))
    if nobase:
        lines.append("groupremove base")
    lines.append("run")
    return "\n".join(lines) + "\n"


def _run_yum_install(rootdir: str, yum_config_path: str, yum_script_path: str) -> None:
    """
    Install the container's package set via "yum shell", then remove the
    kernel-related packages that don't belong inside an OpenVZ container.
    """
    print("Start installing packages")
    utils.subprocess_call(
        [
            "yum",
            "shell",
            "--quiet",
            "--config=%s" % yum_config_path,
            "--installroot=%s" % rootdir,
            yum_script_path,
        ],
        ignore_rc=True,
    )
    utils.subprocess_call(
        [
            "yum",
            "remove",
            "kernel",
            "kernel-firmware",
            "dracut",
            "dracut-kernel",
            "dracut-network",
            "fcoe-utils",
            "libdrm",
            "lldpad",
            "plymouth",
            "-y",
            "--quiet",
            "--config=%s" % yum_config_path,
            "--installroot=%s" % rootdir,
        ],
        ignore_rc=True,
    )
    print("Packages installed")


def _move_script_into_chroot(rootdir: str, script_path: str, content: str) -> None:
    """
    Write `content` to `script_path` and move it under `rootdir`, so it's
    reachable at the same path once chrooted into `rootdir`.
    """
    with open(script_path, "w") as fh:
        fh.write(content)
    shutil.move(script_path, os.path.join(rootdir, script_path.lstrip("/")))


def _apply_services_script(
    rootdir: str, sysname: str, enabled: List[str], disabled: List[str]
) -> None:
    """
    Generate a chkconfig on/off script from the kickstart's services directive
    and run it inside the container via chroot.
    """
    print("Disabling and enabling services as needed")
    script_path = "/tmp/%s-services.sh" % sysname
    lines = ["chkconfig --level 345 %s off" % service for service in disabled]
    lines += ["chkconfig --level 345 %s on" % service for service in enabled]
    content = "\n".join(lines) + ("\n" if lines else "")
    _move_script_into_chroot(rootdir, script_path, content)
    utils.subprocess_call(["chroot", rootdir, "/bin/bash", script_path], ignore_rc=True)


def _apply_post_install_script(
    rootdir: str, sysname: str, interpreter: str, script_body: str
) -> None:
    """
    Write out the kickstart's %post script and run it inside the container
    via chroot, using the interpreter declared in the kickstart file.
    """
    print("Perform post-installation actions")
    script_path = "/tmp/%s-post-install" % sysname
    _move_script_into_chroot(rootdir, script_path, script_body)
    utils.subprocess_call(["chroot", rootdir, interpreter, script_path], ignore_rc=True)


_STALE_UPSTART_CONFIGS = [
    "etc/init/control-alt-delete.conf",
    "etc/init/plymouth-shutdown.conf",
    "etc/init/prefdm.conf",
    "etc/init/quit-plymouth.conf",
    "etc/init/rcS-sulogin.conf",
    "etc/init/serial.conf",
    "etc/init/start-ttys.conf",
    "etc/init/tty.conf",
]

# BSD-style pty/tty device names, e.g. ptya0, ptyp0, ttya0, ttyp0, ...
_PTY_DEVICE_NAMES = [
    "%sty%s%s" % (first, second, suffix)
    for first in "pt"
    for second in "ap"
    for suffix in "0123456789abcdef"
]

_STATIC_DEVICE_NAMES = [
    "console",
    "core",
    "full",
    "kmem",
    "kmsg",
    "mem",
    "null",
    "port",
    "ptmx",
    "random",
    "urandom",
    "zero",
    "ram0",
]

_STDIO_SYMLINKS = [
    ("fd", "/proc/self/fd"),
    ("stderr", "/proc/self/fd/2"),
    ("stdin", "/proc/self/fd/0"),
    ("stdout", "/proc/self/fd/1"),
]


def _comment_out_console_lines(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path) as fh:
        content = fh.read()
    content = re.sub(r"^console", "#console", content, flags=re.MULTILINE)
    with open(path, "w") as fh:
        fh.write(content)


def _disable_gssapi_authentication(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path) as fh:
        content = fh.read()
    content = content.replace("GSSAPIAuthentication yes", "GSSAPIAuthentication no")
    with open(path, "w") as fh:
        fh.write(content)


def _set_root_password_hash(path: str, rootpw: Optional[str]) -> None:
    if not rootpw or not os.path.exists(path):
        return
    with open(path) as fh:
        content = fh.read()
    content = re.sub(r"root:.:", "root:%s:" % rootpw, content, count=1)
    with open(path, "w") as fh:
        fh.write(content)


def _replace_symlink(link_path: str, target: str) -> None:
    if os.path.lexists(link_path):
        os.remove(link_path)
    os.symlink(target, link_path)


def _recreate_device_nodes(device_dir: str) -> None:
    utils.subprocess_call(
        ["/sbin/MAKEDEV", "-d", device_dir, "-x"]
        + _PTY_DEVICE_NAMES
        + _STATIC_DEVICE_NAMES,
        ignore_rc=True,
    )
    for name, target in _STDIO_SYMLINKS:
        _replace_symlink(os.path.join(device_dir, name), target)


def _tune_container_tree(rootdir: str, rootpw: Optional[str]) -> None:
    """
    Adjust a freshly-installed root filesystem to be suitable for running as
    an OpenVZ container (as opposed to a standalone/physical install).
    """
    print("Make the tree container-ready")

    for relative_path in _STALE_UPSTART_CONFIGS:
        path = os.path.join(rootdir, relative_path)
        if os.path.exists(path):
            os.remove(path)

    _comment_out_console_lines(os.path.join(rootdir, "etc/init/rc.conf"))
    _comment_out_console_lines(os.path.join(rootdir, "etc/init/rcS.conf"))

    _disable_gssapi_authentication(os.path.join(rootdir, "etc/ssh/sshd_config"))

    selinux_dir = os.path.join(rootdir, "etc/selinux")
    os.makedirs(selinux_dir, exist_ok=True)
    with open(os.path.join(selinux_dir, "config"), "w") as fh:
        fh.write("SELINUX=disabled\n")

    _set_root_password_hash(os.path.join(rootdir, "etc/shadow"), rootpw)

    _replace_symlink(os.path.join(rootdir, "etc/mtab"), "/proc/mounts")

    with open(os.path.join(rootdir, "etc/fstab"), "w") as fh:
        fh.write("none  /dev/pts    devpts  rw,gid=5,mode=620   0   0\n")

    dev_null_path = os.path.join(rootdir, "dev/null")
    if os.path.exists(dev_null_path):
        os.remove(dev_null_path)

    _recreate_device_nodes(os.path.join(rootdir, "dev"))
    _recreate_device_nodes(os.path.join(rootdir, "etc/udev/devices"))

    os.chmod(os.path.join(rootdir, "tmp"), 0o1777)
    os.chmod(os.path.join(rootdir, "var/tmp"), 0o1777)


def _install_container_tree(sysname: str, kickstart_url: str, rootdir: str) -> None:
    """
    Populate an OpenVZ container's root filesystem from a kickstart file:
    install packages via yum, enable/disable services, run the post-install
    script, and tune the resulting tree to run as a container.
    """
    kickstart_text = utils.urlread(kickstart_url)
    if isinstance(kickstart_text, bytes):
        kickstart_text = kickstart_text.decode()

    rootpw = _extract_rootpw(kickstart_text)
    interpreter = _extract_post_install_interpreter(kickstart_text)
    post_install_script = _extract_post_install_script(kickstart_text)
    enabled, disabled = _extract_services(kickstart_text)
    base_repo_url = _extract_base_repo_url(kickstart_text)
    ignore_missing = _extract_ignoremissing(kickstart_text)
    repos = _extract_repos(kickstart_text)
    nobase = _extract_nobase(kickstart_text)
    packages = _extract_packages(kickstart_text)

    yum_config_path = "/tmp/%s-yum.cfg" % sysname
    yum_script_path = "/tmp/%s-yum.yum" % sysname
    with open(yum_config_path, "w") as fh:
        fh.write(_build_yum_config(base_repo_url, ignore_missing, repos))
    with open(yum_script_path, "w") as fh:
        fh.write(_build_yum_script(packages, nobase))

    _run_yum_install(rootdir, yum_config_path, yum_script_path)

    for repo_file in glob.glob(os.path.join(rootdir, "etc/yum.repos.d/*.repo")):
        os.remove(repo_file)

    _apply_services_script(rootdir, sysname, enabled, disabled)
    _apply_post_install_script(rootdir, sysname, interpreter, post_install_script)
    _tune_container_tree(rootdir, rootpw)

    print("All done")


def start_install(*args: Any, **kwargs: Any) -> Optional[int]:
    # check for Openvz tools presence
    # can be this apps installed in some other place?
    vzcfgvalidate = "/usr/sbin/vzcfgvalidate"
    vzctl = "/usr/sbin/vzctl"
    if not os.path.exists(vzcfgvalidate) or not os.path.exists(vzctl):
        raise OVZCreateException(
            "Cannot find %s and/or %s! Are OpenVZ tools installed?"
            % (vzcfgvalidate, vzctl)
        )

    # params, that can be defined/redefined through autoinstall_meta
    keys_for_meta = [
        "KMEMSIZE",  # "14372700:14790164",
        "LOCKEDPAGES",  # "2048:2048",
        "PRIVVMPAGES",  # "65536:69632",
        "SHMPAGES",  # "21504:21504",
        "NUMPROC",  # "240:240",
        "VMGUARPAGES",  # "33792:unlimited",
        "OOMGUARPAGES",  # "26112:unlimited",
        "NUMTCPSOCK",  # "360:360",
        "NUMFLOCK",  # "188:206",
        "NUMPTY",  # "16:16",
        "NUMSIGINFO",  # "256:256",
        "TCPSNDBUF",  # "1720320:2703360",
        "TCPRCVBUF",  # "1720320:2703360",
        "OTHERSOCKBUF",  # "1126080:2097152",
        "DGRAMRCVBUF",  # "262144:262144",
        "NUMOTHERSOCK",  # "120",
        "DCACHESIZE",  # "3409920:3624960",
        "NUMFILE",  # "9312:9312",
        "AVNUMPROC",  # "180:180",
        "NUMIPTENT",  # "128:128",
        "DISKINODES",  # "200000:220000",
        "QUOTATIME",  # "0",
        "VE_ROOT",  # "/vz/root/$VEID",
        "VE_PRIVATE",  # "/vz/private/$VEID",
        "SWAPPAGES",  # "0:1G",
        "ONBOOT",  # "yes"
    ]

    sysname = kwargs["name"]
    autoinst = kwargs["profile_data"]["autoinst"]
    # we use it for --ostemplate parameter
    template = kwargs["profile_data"]["breed"]
    hostname = kwargs["profile_data"]["hostname"]
    ipadd = kwargs["profile_data"]["ip_address_eth0"]
    nameserver = kwargs["profile_data"]["name_servers"][0]
    diskspace = kwargs["profile_data"]["virt_file_size"]
    physpages = kwargs["profile_data"]["virt_ram"]
    cpus = kwargs["profile_data"]["virt_cpus"]
    onboot = kwargs["profile_data"]["virt_auto_boot"]

    # we get [0,1] ot [False,True] and have to map it to [no,yes]
    onboot = "yes" if onboot == "1" or onboot else "no"
    ctid: Optional[int] = None
    vz_meta: Dict[str, Any] = {}

    # get all vz_ parameters from autoinstall_meta
    for key, value in kwargs["profile_data"]["autoinstall_meta"]:
        if key.startswith("vz_"):
            vz_meta[key.replace("vz_", "").upper()] = value

    if "CTID" in vz_meta and vz_meta["CTID"]:
        try:
            ctid = int(vz_meta["CTID"])
            del vz_meta["CTID"]
        except ValueError:
            print("Invalid CTID in autoinstall_meta. Exiting...")
            return 1
    else:
        raise OVZCreateException(
            'Mandatory "vz_ctid" parameter not found in autoinstall_meta!'
        )

    confiname = "/etc/vz/conf/%d.conf" % ctid

    # this is the minimal config. we can define additional parameters or
    # override some of them in autoinstall_meta
    min_config = {
        "PHYSPAGES": "0:%sM" % physpages,
        "SWAPPAGES": "0:1G",
        "DISKSPACE": "%sG:%sG" % (diskspace, diskspace),
        "DISKINODES": "200000:220000",
        "QUOTATIME": "0",
        "CPUUNITS": "1000",
        "CPUS": cpus,
        "VE_ROOT": "/vz/root/$VEID",
        "VE_PRIVATE": "/vz/private/$VEID",
        "OSTEMPLATE": template,
        "NAME": sysname,
        "HOSTNAME": hostname,
        "IP_ADDRESS": ipadd,
        "NAMESERVER": nameserver,
    }

    # merge with override
    full_config = dict(
        [
            (k, vz_meta[k] if k in vz_meta and k in keys_for_meta else min_config[k])
            for k in set(min_config.keys()) | set(vz_meta.keys())
        ]
    )

    # write config file for container
    f = open(confiname, "w+")
    for key, val in full_config.items():
        f.write('%s="%s"\n' % (key, val))
    f.close()

    # validate the config file
    cmd = [vzcfgvalidate, confiname]
    if subprocess.call(cmd) == 0:
        # now install the container tree
        try:
            _install_container_tree(
                sysname,
                autoinst,
                full_config["VE_PRIVATE"].replace("$VEID", "%d" % ctid),
            )
        except Exception:
            raise OVZCreateException("Container creation %s failed" % ctid)
        # if everything fine, start the container
        cmd = [vzctl, "start", str(ctid)]
        if subprocess.call(cmd) != 0:
            raise OVZCreateException("Start container %s failed" % ctid)
    else:
        raise OVZCreateException("Container %s config file is not valid" % ctid)
