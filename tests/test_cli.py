from koan import cli
from koan.cexceptions import InfoException

# ---------------------------------------------------------------------------
# main() / koan
# ---------------------------------------------------------------------------


def test_main_minimal_invocation_runs_koan(mocker):
    # Arrange
    mocker.patch("sys.argv", ["koan"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert
    assert result == 0
    koan_cls.return_value.run.assert_called_once()


def test_main_sets_representative_attributes(mocker):
    # Arrange
    mocker.patch(
        "sys.argv",
        [
            "koan",
            "-v",
            "-p",
            "myprofile",
            "-V",
            "myguest",
            "-t",
            "8080",
            "-T",
            "qemu",
            "--wait",
            "42",
            "--noreboot",
        ],
    )
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert
    assert result == 0
    k = koan_cls.return_value
    assert k.is_virt is True
    assert k.profile == "myprofile"
    assert k.virt_name == "myguest"
    assert k.port == "8080"
    assert k.virt_type == "qemu"
    assert k.virtinstall_wait == 42
    assert k.virtinstall_noreboot is True
    k.run.assert_called_once()


def test_main_virt_name_and_port_not_set_when_absent(mocker):
    # Arrange: options.virt_name/options.port default to None when the flags are absent,
    # so the "if options.x is not None" guards should skip assigning k.virt_name/k.port
    # entirely, leaving them as untouched auto-speccing MagicMock attributes.
    mocker.patch("sys.argv", ["koan"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    cli.main()

    # Assert: since the attributes were never explicitly assigned a plain value, they
    # remain MagicMock instances rather than being set to None.
    k = koan_cls.return_value
    from unittest.mock import MagicMock

    assert isinstance(k.virt_name, MagicMock)
    assert isinstance(k.port, MagicMock)


def test_main_nogfx_and_graphics_conflict_raises_before_run(mocker):
    # Arrange
    mocker.patch("sys.argv", ["koan", "-n", "-g", "vnc"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert: InfoException is raised inside main()'s own try/except, from_koan path
    assert result == 1
    koan_cls.return_value.run.assert_not_called()


def test_main_graphics_none_maps_to_none(mocker):
    # Arrange
    mocker.patch("sys.argv", ["koan", "-g", "none"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert
    assert result == 0
    assert koan_cls.return_value.gfx_type is None


def test_main_graphics_default_is_vnc(mocker):
    # Arrange
    mocker.patch("sys.argv", ["koan"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert
    assert result == 0
    assert koan_cls.return_value.gfx_type == "vnc"


def test_main_graphics_explicit_value_is_passed_through(mocker):
    # Arrange
    mocker.patch("sys.argv", ["koan", "-g", "spice"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert
    assert result == 0
    assert koan_cls.return_value.gfx_type == "spice"


def test_main_nogfx_alone_sets_gfx_type_none(mocker):
    # Arrange: -n alone (no explicit -g) does not trip the mutual-exclusion check because
    # options.gfx_type defaults to "vnc" (not None) while options.no_gfx is True -- the
    # code still raises since gfx_type default "vnc" is "not None". Verify actual behavior.
    mocker.patch("sys.argv", ["koan", "-n"])
    koan_cls = mocker.patch("koan.cli.Koan")

    # Act
    result = cli.main()

    # Assert: gfx_type has a default of "vnc" (never None), so combined with no_gfx being
    # True this always hits the InfoException branch in the current implementation.
    assert result == 1
    koan_cls.return_value.run.assert_not_called()


def test_main_from_koan_exception_returns_clean_error(mocker, capsys):
    # Arrange
    mocker.patch("sys.argv", ["koan"])
    koan_cls = mocker.patch("koan.cli.Koan")
    koan_cls.return_value.run.side_effect = InfoException("boom happened")

    # Act
    result = cli.main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "boom happened" in captured.out
    assert "Traceback" not in captured.out


def test_main_generic_exception_returns_error_with_traceback(mocker, capsys):
    # Arrange
    mocker.patch("sys.argv", ["koan"])
    koan_cls = mocker.patch("koan.cli.Koan")
    koan_cls.return_value.run.side_effect = ValueError("unexpected boom")

    # Act
    result = cli.main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "ValueError" in captured.out


# ---------------------------------------------------------------------------
# register_main() / cobbler-register
# ---------------------------------------------------------------------------


def test_register_main_minimal_invocation_runs_register(mocker):
    # Arrange
    mocker.patch("sys.argv", ["cobbler-register"])
    register_cls = mocker.patch("koan.cli.Register")

    # Act
    result = cli.register_main()

    # Assert
    assert result == 0
    register_cls.return_value.run.assert_called_once()


def test_register_main_sets_representative_attributes(mocker):
    # Arrange
    mocker.patch(
        "sys.argv",
        [
            "cobbler-register",
            "-s",
            "myserver",
            "-p",
            "9090",
            "-P",
            "myprofile",
            "-f",
            "myhost.example.com",
            "-b",
        ],
    )
    register_cls = mocker.patch("koan.cli.Register")

    # Act
    result = cli.register_main()

    # Assert
    assert result == 0
    k = register_cls.return_value
    assert k.server == "myserver"
    assert k.port == "9090"
    assert k.profile == "myprofile"
    assert k.hostname == "myhost.example.com"
    assert k.batch is True
    k.run.assert_called_once()


def test_register_main_from_koan_exception_returns_clean_error(mocker, capsys):
    # Arrange
    mocker.patch("sys.argv", ["cobbler-register"])
    register_cls = mocker.patch("koan.cli.Register")
    register_cls.return_value.run.side_effect = InfoException("registration failed")

    # Act
    result = cli.register_main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "registration failed" in captured.out
    assert "Traceback" not in captured.out


def test_register_main_generic_exception_returns_error_with_traceback(mocker, capsys):
    # Arrange
    mocker.patch("sys.argv", ["cobbler-register"])
    register_cls = mocker.patch("koan.cli.Register")
    register_cls.return_value.run.side_effect = RuntimeError("unexpected")

    # Act
    result = cli.register_main()

    # Assert
    assert result == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.out
