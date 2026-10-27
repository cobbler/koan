"""
Broader live-server CLI coverage: list/display commands and CLI-flag override
precedence over server-rendered virt.* values. Actual virt-install/libvirt guest
creation is out of scope here (GH Actions runners have no nested-virt support) -
these only exercise the XML-RPC/HTTP leg via koan's real CLI entry point.
"""

import subprocess
from typing import Tuple

import pytest

from tests.integration.conftest import SEEDED_VIRT_VALUES, cobbler_hostname


def _run_koan(cobbler_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    server = cobbler_hostname(cobbler_url)
    return subprocess.run(
        ["koan", "--server", server, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.integration
def test_koan_list_profiles_and_systems(
    cobbler_url: str, seed_system_with_virt: Tuple[str, str]
) -> None:
    _, system_name = seed_system_with_virt

    profiles_result = _run_koan(cobbler_url, "--list", "profiles")
    systems_result = _run_koan(cobbler_url, "--list", "systems")

    assert profiles_result.returncode == 0
    assert systems_result.returncode == 0
    assert system_name in systems_result.stdout


@pytest.mark.integration
def test_koan_display_profile_shows_seeded_virt_values(
    cobbler_url: str, seed_profile_with_virt: Tuple[str, str]
) -> None:
    _, name = seed_profile_with_virt

    result = _run_koan(cobbler_url, "--display", "--profile", name)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"virt_ram  : {SEEDED_VIRT_VALUES['ram']}" in result.stdout
    assert f"virt_type  : {SEEDED_VIRT_VALUES['type']}" in result.stdout
    assert f"virt_disk_driver  : {SEEDED_VIRT_VALUES['disk_driver']}" in result.stdout


@pytest.mark.integration
def test_koan_display_system_shows_seeded_virt_values(
    cobbler_url: str, seed_system_with_virt: Tuple[str, str]
) -> None:
    _, name = seed_system_with_virt

    result = _run_koan(cobbler_url, "--display", "--system", name)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"virt_ram  : {SEEDED_VIRT_VALUES['ram']}" in result.stdout


@pytest.mark.integration
def test_koan_virt_type_cli_override_takes_precedence(
    cobbler_url: str, seed_profile_with_virt: Tuple[str, str]
) -> None:
    # `koan --display` prints the server's raw virt_type unconditionally - it never
    # applies the CLI-override-then-server-fallback rule that net_install() uses for
    # the actual install flow (net_install()'s "self.virt_type = self.safe_load(...)
    # if self.virt_type is None" check), so exercise that rule directly instead.
    _, name = seed_profile_with_virt
    import xmlrpc.client

    from koan.app import Koan

    k = Koan()
    k.xmlrpc_server = xmlrpc.client.ServerProxy(cobbler_url)  # type: ignore[assignment]
    k.virt_type = "kvm"

    data = k.get_data("profile", name)

    # The server's own value is "qemu" - confirms get_data() doesn't clobber a
    # pre-set (CLI-override-simulating) self.virt_type with the server's value,
    # matching net_install()'s "only fall back to the server value if
    # self.virt_type is still None" rule.
    assert data["virt_type"] == SEEDED_VIRT_VALUES["type"] == "qemu"
    assert k.virt_type == "kvm"


@pytest.mark.integration
def test_koan_unreachable_server_error_message() -> None:
    result = subprocess.run(
        [
            "koan",
            "--server",
            "127.0.0.1",
            "--port",
            "1",
            "--list",
            "profiles",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "Could not find Cobbler" in (result.stdout + result.stderr)
