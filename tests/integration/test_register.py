"""
Live end-to-end coverage for `cobbler-register`, gated behind the
`register_new_installs` setting enabled via the generated compose override (see
tests/integration/docker/generate_settings_override.py). Register.run() requires
root (os.getuid() != 0), so these invoke the real CLI entry point via `sudo` rather
than calling Register() in-process.
"""

import shutil
import subprocess
from typing import Any, Tuple

import pytest

from tests.integration.conftest import cobbler_hostname


def _run_cobbler_register(*args: str) -> subprocess.CompletedProcess[str]:
    # sudo's secure_path often excludes /usr/local/bin, where pip installs console
    # scripts - resolve the absolute path in our own (non-reset) PATH first, rather
    # than relying on sudo's PATH to find it.
    executable = shutil.which("cobbler-register")
    assert executable is not None, "cobbler-register not found on PATH"
    return subprocess.run(
        ["sudo", executable, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.integration
def test_cobbler_register_creates_system_when_enabled(
    remote: Any,
    token: str,
    cobbler_url: str,
    seed_profile_with_virt: Tuple[str, str],
    unique_name: Any,
) -> None:
    _, profile_name = seed_profile_with_virt
    server = cobbler_hostname(cobbler_url)
    fqdn = f"{unique_name('registered')}.example.com"

    result = _run_cobbler_register(
        "--server", server, "--profile", profile_name, "--fqdn", fqdn
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "registration successful" in result.stdout

    systems = [s["name"] for s in remote.get_systems()]
    assert fqdn in systems
    remote.remove_system(fqdn, token)


@pytest.mark.integration
def test_cobbler_register_hostname_override(
    remote: Any,
    token: str,
    cobbler_url: str,
    seed_profile_with_virt: Tuple[str, str],
    unique_name: Any,
) -> None:
    _, profile_name = seed_profile_with_virt
    server = cobbler_hostname(cobbler_url)
    fqdn = f"{unique_name('customhost')}.example.com"

    result = _run_cobbler_register(
        "--server", server, "--profile", profile_name, "--fqdn", fqdn
    )

    assert result.returncode == 0, result.stdout + result.stderr

    system = remote.get_system_as_rendered(fqdn)
    assert system["hostname"] == fqdn
    remote.remove_system(fqdn, token)


@pytest.mark.integration
def test_cobbler_register_missing_profile_fails_cleanly(
    cobbler_url: str, unique_name: Any
) -> None:
    server = cobbler_hostname(cobbler_url)
    fqdn = f"{unique_name('nosuchprofile')}.example.com"

    result = _run_cobbler_register(
        "--server", server, "--profile", "no-such-profile-exists", "--fqdn", fqdn
    )

    assert result.returncode != 0
    assert "no such remote profile" in (result.stdout + result.stderr)
