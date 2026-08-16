"""
Shared fixtures for koan's live-server integration test suite.

These tests require a real, running Cobbler server - they are NOT run by default
(see pytest.ini's "not integration" addopts). Run them explicitly with:

    pytest tests/integration -m integration -v

against a server reachable at KOAN_IT_COBBLER_URL (default: http://localhost/cobbler_api).
See tests/integration/docker/generate_settings_override.py and
.github/workflows/integration.yml for how CI brings one up.

The server must have two zero-byte fixture files already present on its filesystem
(created by the CI workflow / local dev-stack setup, not by these fixtures, since they
must exist on the *server's* filesystem, not the machine running pytest):
    /var/lib/cobbler/fixtures/vmlinuz_test
    /var/lib/cobbler/fixtures/initrd_test.img
"""

import os
import time
import urllib.parse
import uuid
import xmlrpc.client
from typing import Any, Callable, Generator, List, Optional, Tuple

import pytest

DEFAULT_COBBLER_URL = "http://localhost/cobbler_api"
DEFAULT_USERNAME = "cobbler"
DEFAULT_PASSWORD = "cobbler"

FIXTURE_KERNEL_PATH = "/var/lib/cobbler/fixtures/vmlinuz_test"
FIXTURE_INITRD_PATH = "/var/lib/cobbler/fixtures/initrd_test.img"

AttrArgs = List[Tuple[List[str], Any]]


def wait_for_cobblerd(
    remote: Any, timeout: float = 60.0, interval: float = 1.0
) -> None:
    """
    Poll the server's XML-RPC endpoint until it responds, rather than assuming a
    fixed sleep is long enough for the container/compose stack to finish starting.
    """
    deadline = time.monotonic() + timeout
    last_error: BaseException = TimeoutError("no attempt was made")
    while time.monotonic() < deadline:
        try:
            remote.ping()
            return
        except (OSError, xmlrpc.client.ProtocolError) as error:
            last_error = error
            time.sleep(interval)
    raise TimeoutError(
        "Cobbler server's XML-RPC endpoint did not become reachable within "
        f"{timeout}s"
    ) from last_error


@pytest.fixture(scope="session", name="cobbler_url")
def fixture_cobbler_url() -> str:
    return os.environ.get("KOAN_IT_COBBLER_URL", DEFAULT_COBBLER_URL)


def cobbler_hostname(cobbler_url: str) -> str:
    """Extract the bare hostname from cobbler_url, for --server/--server flags."""
    hostname = urllib.parse.urlparse(cobbler_url).hostname
    assert hostname is not None, f"Could not parse a hostname out of {cobbler_url!r}"
    return hostname


@pytest.fixture(scope="session", name="remote")
def fixture_remote(cobbler_url: str) -> Any:
    """
    A real network XML-RPC client, exactly like koan's own connect_to_server()
    produces - not an in-process shortcut.
    """
    remote = xmlrpc.client.ServerProxy(cobbler_url)
    try:
        wait_for_cobblerd(remote)
    except TimeoutError as error:
        pytest.fail(str(error))
    return remote


@pytest.fixture(scope="session", name="token")
def fixture_token(remote: Any) -> str:
    """
    Real username/password auth against authentication.configfile, matching how
    koan itself (and a human operator) authenticates - not a local shared-secret
    file, which an external client cannot read anyway.
    """
    username = os.environ.get("KOAN_IT_COBBLER_USER", DEFAULT_USERNAME)
    password = os.environ.get("KOAN_IT_COBBLER_PASSWORD", DEFAULT_PASSWORD)
    token = remote.login(username, password)
    if not token:
        pytest.fail("Could not obtain an XML-RPC token from the Cobbler server")
    return token


@pytest.fixture(name="unique_name")
def fixture_unique_name() -> Callable[[str], str]:
    """
    Generates collision-free object names, since tests run against a shared,
    possibly-reused server rather than a freshly-seeded one per test.
    """

    def _unique_name(prefix: str) -> str:
        return f"koan-it-{prefix}-{uuid.uuid4().hex[:8]}"

    return _unique_name


@pytest.fixture(name="unique_mac")
def fixture_unique_mac() -> Callable[[], str]:
    """
    Generates collision-free MAC addresses (Cobbler rejects duplicate MACs across
    systems by default), since tests run against a shared, possibly-reused server.
    """

    def _unique_mac() -> str:
        # 4 more octets after the fixed "52:54" locally-administered prefix = 6 total.
        octets = uuid.uuid4().hex[:8]
        return "52:54:" + ":".join(octets[i : i + 2] for i in range(0, 8, 2))

    return _unique_mac


def _name_from_args(args: AttrArgs) -> Optional[str]:
    """remove_distro/remove_profile/remove_system all take a NAME, not a uid - pull
    it out of the (["name"], value) pair every caller is expected to include."""
    for key, value in args:
        if key == ["name"]:
            return str(value)
    return None


@pytest.fixture(name="create_distro")
def fixture_create_distro(
    remote: Any, token: str
) -> Generator[Callable[[AttrArgs], str], None, None]:
    created: List[str] = []

    def _create_distro(args: AttrArgs) -> str:
        did = remote.new_distro(token)
        for key, value in args:
            remote.modify_distro(did, key, value, token)
        remote.save_distro(did, True, True, "new", token)
        name = _name_from_args(args)
        if name is not None:
            created.append(name)
        return did

    yield _create_distro

    for name in created:
        try:
            remote.remove_distro(name, token)
        except xmlrpc.client.Fault:
            pass


@pytest.fixture(name="create_profile")
def fixture_create_profile(
    remote: Any, token: str
) -> Generator[Callable[[AttrArgs], str], None, None]:
    created: List[str] = []

    def _create_profile(args: AttrArgs) -> str:
        pid = remote.new_profile(token)
        for key, value in args:
            remote.modify_profile(pid, key, value, token)
        remote.save_profile(pid, True, True, "new", token)
        name = _name_from_args(args)
        if name is not None:
            created.append(name)
        return pid

    yield _create_profile

    for name in created:
        try:
            remote.remove_profile(name, token)
        except xmlrpc.client.Fault:
            pass


@pytest.fixture(name="create_system")
def fixture_create_system(
    remote: Any, token: str
) -> Generator[Callable[[AttrArgs], str], None, None]:
    created: List[str] = []

    def _create_system(args: AttrArgs) -> str:
        sid = remote.new_system(token)
        for key, value in args:
            remote.modify_system(sid, key, value, token)
        remote.save_system(sid, True, True, "new", token)
        name = _name_from_args(args)
        if name is not None:
            created.append(name)
        return sid

    yield _create_system

    for name in created:
        try:
            remote.remove_system(name, token)
        except xmlrpc.client.Fault:
            pass


@pytest.fixture(name="create_network_interface")
def fixture_create_network_interface(
    remote: Any, token: str
) -> Callable[[str, AttrArgs], str]:
    def _create_network_interface(sid: str, args: AttrArgs) -> str:
        nid = remote.new_network_interface(sid, token)
        for key, value in args:
            remote.modify_network_interface(nid, key, value, token)
        remote.save_network_interface(nid, True, True, "new", token)
        return nid

    return _create_network_interface


# A fixed, known set of virt.* values every test that seeds a Profile/System can
# assert against - distinct from every field's default so a silent fallback to
# defaults (the original bug class) would be caught immediately.
SEEDED_VIRT_VALUES = {
    "ram": 2048,
    "cpus": 4,
    "disk_driver": "qcow2",
    "file_size": 10.0,
    "path": "/var/lib/libvirt/images",
    "pxe_boot": True,
    "auto_boot": True,
    "type": "qemu",
    "uefi": True,
}


@pytest.fixture(name="seeded_distro")
def fixture_seeded_distro(
    create_distro: Callable[[AttrArgs], str], unique_name: Callable[[str], str]
) -> str:
    return create_distro(
        [
            (["name"], unique_name("distro")),
            (["arch"], "x86_64"),
            (["breed"], "generic"),
            (["kernel"], FIXTURE_KERNEL_PATH),
            (["initrd"], FIXTURE_INITRD_PATH),
        ]
    )


@pytest.fixture(name="seed_profile_with_virt")
def fixture_seed_profile_with_virt(
    create_profile: Callable[[AttrArgs], str],
    seeded_distro: str,
    unique_name: Callable[[str], str],
) -> Tuple[str, str]:
    """
    Returns (profile_uid, profile_name) for a freshly-created Profile with
    SEEDED_VIRT_VALUES applied via the two-element ["virt", field] attribute path.
    """
    name = unique_name("profile")
    args: AttrArgs = [(["name"], name), (["distro"], seeded_distro)]
    args += [(["virt", field], value) for field, value in SEEDED_VIRT_VALUES.items()]
    pid = create_profile(args)
    return pid, name


@pytest.fixture(name="seed_system_with_virt")
def fixture_seed_system_with_virt(
    create_system: Callable[[AttrArgs], str],
    create_network_interface: Callable[[str, AttrArgs], str],
    seed_profile_with_virt: Tuple[str, str],
    unique_name: Callable[[str], str],
    unique_mac: Callable[[], str],
) -> Tuple[str, str]:
    """
    Returns (system_uid, system_name) for a freshly-created System (attached to the
    seed_profile_with_virt profile) with SEEDED_VIRT_VALUES applied the same way,
    plus a NIC (needed for e.g. cobbler-register-style flows).
    """
    profile_uid, _ = seed_profile_with_virt
    name = unique_name("system")
    args: AttrArgs = [(["name"], name), (["profile"], profile_uid)]
    args += [(["virt", field], value) for field, value in SEEDED_VIRT_VALUES.items()]
    sid = create_system(args)
    create_network_interface(
        sid,
        [
            (["name"], "default"),
            (["mac_address"], unique_mac()),
        ],
    )
    return sid, name
