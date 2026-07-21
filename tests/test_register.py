from unittest.mock import MagicMock

import pytest

from koan.cexceptions import InfoException
from koan.register import Register


def make_register(**attrs):
    """Build a Register() instance with the given attributes overridden."""
    reg = Register()
    for key, value in attrs.items():
        setattr(reg, key, value)
    return reg


def test_run_requires_root(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=1000)
    reg = make_register()

    # Act / Assert
    with pytest.raises(InfoException, match="root access is required to register"):
        reg.run()


def test_run_happy_path(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "other"}, {"name": "webserver"}]
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={"eth0": {}})
    getfqdn = mocker.patch("koan.register.socket.getfqdn")

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="myhost.example.com",
        batch="",
    )

    # Act
    reg.run()

    # Assert
    getfqdn.assert_not_called()
    mock_conn.register_new_system.assert_called_once_with(
        {
            "interfaces": {"eth0": {}},
            "name": "myhost.example.com",
            "profile": "webserver",
            "hostname": "myhost.example.com",
        }
    )


def test_run_hostname_auto_with_unresolvable_fqdn(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "webserver"}]
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})
    mocker.patch("koan.register.socket.getfqdn", return_value="localhost.localdomain")
    mocker.patch("koan.register.time.time", return_value=1234.5678)

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="*AUTO*",
        batch="",
    )

    # Act
    reg.run()

    # Assert
    mock_conn.register_new_system.assert_called_once_with(
        {
            "interfaces": {},
            "name": str(1234.5678),
            "profile": "webserver",
            "hostname": "",
        }
    )


def test_run_hostname_blank_resolves_via_getfqdn(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "webserver"}]
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})
    mocker.patch("koan.register.socket.getfqdn", return_value="discovered.example.com")

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="",
        batch="",
    )

    # Act
    reg.run()

    # Assert
    mock_conn.register_new_system.assert_called_once_with(
        {
            "interfaces": {},
            "name": "discovered.example.com",
            "profile": "webserver",
            "hostname": "discovered.example.com",
        }
    )


def test_run_missing_fqdn_raises(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})
    mocker.patch("koan.register.socket.getfqdn", return_value="localhost.localdomain")

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="",
        batch="",
    )

    # Act / Assert
    with pytest.raises(InfoException, match="must specify --fqdn, could not discover"):
        reg.run()

    mock_conn.register_new_system.assert_not_called()


def test_run_missing_profile_raises(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="",
        hostname="myhost.example.com",
        batch="",
    )

    # Act / Assert
    with pytest.raises(InfoException, match="must specify --profile"):
        reg.run()

    mock_conn.get_profiles.assert_not_called()
    mock_conn.register_new_system.assert_not_called()


def test_run_profile_not_found_raises(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "other"}]
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="myhost.example.com",
        batch="",
    )

    # Act / Assert
    with pytest.raises(
        InfoException, match="no such remote profile, see 'koan --list-profiles'"
    ):
        reg.run()

    mock_conn.register_new_system.assert_not_called()


def test_run_batch_registration_succeeds(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "webserver"}]
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="myhost.example.com",
        batch=True,
    )

    # Act
    result = reg.run()

    # Assert
    assert result is None
    mock_conn.register_new_system.assert_called_once()


def test_run_batch_swallows_registration_failure(mocker):
    # Arrange
    mocker.patch("koan.register.os.getuid", return_value=0)
    mock_conn = MagicMock()
    mock_conn.get_profiles.return_value = [{"name": "webserver"}]
    mock_conn.register_new_system.side_effect = RuntimeError("boom")
    mocker.patch("koan.register.utils.connect_to_server", return_value=mock_conn)
    mocker.patch("koan.register.utils.get_network_info", return_value={})
    mocker.patch("koan.register.traceback.print_exc")

    reg = make_register(
        server="cobbler.example.com",
        port="80",
        profile="webserver",
        hostname="myhost.example.com",
        batch=True,
    )

    # Act
    result = reg.run()

    # Assert
    assert result is None
    mock_conn.register_new_system.assert_called_once()
