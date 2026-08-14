"""
Live-server regression coverage for Cobbler's nested "virt" Options object
(see koan/app.py's _flatten_virt_options()). These are the tests that would have
caught the original bug: they validate that a *real* Cobbler server's rendered
output has the shape koan now assumes, not just that koan's own parsing logic is
internally consistent (tests/test_app.py already covers that with mocks).
"""

from typing import Any, Dict, Tuple

import pytest

from koan.app import Koan
from tests.integration.conftest import SEEDED_VIRT_VALUES, AttrArgs


@pytest.mark.integration
def test_get_profile_as_rendered_virt_matches_seeded_values(
    remote: Any, seed_profile_with_virt: Tuple[str, str]
) -> None:
    _, name = seed_profile_with_virt

    rendered = remote.get_profile_as_rendered(name)

    assert rendered["virt"] == SEEDED_VIRT_VALUES


@pytest.mark.integration
def test_get_system_as_rendered_virt_matches_seeded_values(
    remote: Any, seed_system_with_virt: Tuple[str, str]
) -> None:
    _, name = seed_system_with_virt

    rendered = remote.get_system_as_rendered(name)

    assert rendered["virt"] == SEEDED_VIRT_VALUES
    # Per-NIC virt_bridge is a separate, unaffected-by-this-migration mechanism -
    # confirm it's still nested under interfaces, not absorbed into "virt" too.
    assert "virt_bridge" in rendered["interfaces"]["default"]


@pytest.mark.integration
def test_get_image_as_rendered_virt_matches_seeded_values(
    remote: Any,
    token: str,
    create_distro: Any,
    unique_name: Any,
) -> None:
    did = create_distro(
        [
            (["name"], unique_name("distro-for-image")),
            (["arch"], "x86_64"),
            (["breed"], "generic"),
            (["kernel"], "/var/lib/cobbler/fixtures/vmlinuz_test"),
            (["initrd"], "/var/lib/cobbler/fixtures/initrd_test.img"),
        ]
    )
    name = unique_name("image")
    iid = remote.new_image(token)
    args: AttrArgs = [(["name"], name)]
    args += [(["virt", field], value) for field, value in SEEDED_VIRT_VALUES.items()]
    for key, value in args:
        remote.modify_image(iid, key, value, token)
    remote.save_image(iid, True, True, "new", token)
    try:
        rendered = remote.get_image_as_rendered(name)
        assert rendered["virt"] == SEEDED_VIRT_VALUES
    finally:
        remote.remove_image(name, token)
        remote.remove_distro(did, token)


@pytest.mark.integration
def test_get_distro_as_rendered_has_no_virt_key(
    remote: Any, seeded_distro: str
) -> None:
    rendered = remote.get_distro_as_rendered(seeded_distro)

    assert "virt" not in rendered


@pytest.mark.integration
def test_modify_profile_virt_requires_two_element_path(
    remote: Any, token: str, create_profile: Any, seeded_distro: str, unique_name: Any
) -> None:
    name = unique_name("profile")
    pid = create_profile([(["name"], name), (["distro"], seeded_distro)])

    # New two-element attribute-path contract: succeeds and actually takes effect.
    assert remote.modify_profile(pid, ["virt", "cpus"], 2, token) is True
    remote.save_profile(pid, True, True, "bypass", token)
    assert remote.get_profile_as_rendered(name)["virt"]["cpus"] == 2

    # Old flat single-string attribute path ("virt_cpus" as one string, not a
    # ["virt", "cpus"] path) is iterated character-by-character by modify_item's
    # getattr/setattr walk, since a plain str is itself iterable - it doesn't raise,
    # but it also doesn't touch the real "virt.cpus" field. This is the concrete
    # "silently does the wrong thing" hazard a client still sending the old flat
    # attribute name would hit against a >= 4.0 server.
    remote.modify_profile(pid, "virt_cpus", 4, token)
    remote.save_profile(pid, True, True, "bypass", token)
    assert remote.get_profile_as_rendered(name)["virt"]["cpus"] == 2


@pytest.mark.integration
def test_koan_virt_flow_end_to_end_against_live_server(
    cobbler_url: str, seed_profile_with_virt: Tuple[str, str]
) -> None:
    """
    The closest thing to a true end-to-end regression test for the whole bug class,
    without actually invoking virt-install/libvirt: drive Koan's real get_data() and
    calc_virt_*() against a live server and confirm they reproduce the seeded values.
    """
    _, name = seed_profile_with_virt
    import xmlrpc.client

    k = Koan()
    k.xmlrpc_server = xmlrpc.client.ServerProxy(cobbler_url)  # type: ignore[assignment]

    data: Dict[str, Any] = k.get_data("profile", name)

    assert k.calc_virt_ram(data) == SEEDED_VIRT_VALUES["ram"]
    assert k.calc_virt_cpus(data) == SEEDED_VIRT_VALUES["cpus"]
    assert k.calc_virt_drivers(data) == [SEEDED_VIRT_VALUES["disk_driver"]]
    assert k.calc_virt_autoboot(data, False) == SEEDED_VIRT_VALUES["auto_boot"]
    assert k.calc_virt_pxeboot(data, False) == SEEDED_VIRT_VALUES["pxe_boot"]
    assert k.safe_load(data, "virt_type", default=None) == SEEDED_VIRT_VALUES["type"]
