from koan.app import Koan


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
