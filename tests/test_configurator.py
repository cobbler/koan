import json
import stat as stat_module

import pytest

from koan.configurator import KoanConfigure


def make_configurator(mocker, config_dict):
    """Helper: build a KoanConfigure instance with os_release mocked out."""
    mocker.patch("koan.configurator.utils.os_release", return_value=("redhat", "7"))
    return KoanConfigure(json.dumps(config_dict))


class TestInit:
    def test_init_sets_config_stats_and_dist(self, mocker):
        # Arrange
        mocker.patch("koan.configurator.utils.os_release", return_value=("redhat", "7"))
        config = {"repos_enabled": True, "packages": {}, "files": {}}

        # Act
        kc = KoanConfigure(json.dumps(config))

        # Assert
        assert kc.config == config
        assert kc.stats == {}
        assert kc.dist == "redhat"

    def test_init_uses_os_release_result(self, mocker):
        # Arrange
        mocker.patch("koan.configurator.utils.os_release", return_value=("suse", "15"))

        # Act
        kc = KoanConfigure(json.dumps({}))

        # Assert
        assert kc.dist == "suse"


class TestConfigureRepos:
    def test_calls_yum_repos_when_yum_available_and_redhat(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {})
        mocker.patch("koan.configurator.yum_available", True)
        yum_repos = mocker.patch.object(kc, "configure_yum_repos")

        # Act
        kc.configure_repos()

        # Assert
        yum_repos.assert_called_once()

    def test_noop_when_yum_not_available(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {})
        mocker.patch("koan.configurator.yum_available", False)
        yum_repos = mocker.patch.object(kc, "configure_yum_repos")

        # Act
        kc.configure_repos()

        # Assert
        yum_repos.assert_not_called()

    def test_noop_when_not_redhat(self, mocker):
        # Arrange
        mocker.patch("koan.configurator.utils.os_release", return_value=("suse", "15"))
        kc = KoanConfigure(json.dumps({}))
        mocker.patch("koan.configurator.yum_available", True)
        yum_repos = mocker.patch.object(kc, "configure_yum_repos")

        # Act
        kc.configure_repos()

        # Assert
        yum_repos.assert_not_called()


class TestConfigurePackages:
    def test_calls_yum_packages_when_yum_available_and_redhat(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {})
        mocker.patch("koan.configurator.yum_available", True)
        yum_packages = mocker.patch.object(kc, "configure_yum_packages")

        # Act
        kc.configure_packages()

        # Assert
        yum_packages.assert_called_once()

    def test_noop_when_yum_not_available(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {})
        mocker.patch("koan.configurator.yum_available", False)
        yum_packages = mocker.patch.object(kc, "configure_yum_packages")

        # Act
        kc.configure_packages()

        # Assert
        yum_packages.assert_not_called()

    def test_noop_when_not_redhat(self, mocker):
        # Arrange
        mocker.patch("koan.configurator.utils.os_release", return_value=("suse", "15"))
        kc = KoanConfigure(json.dumps({}))
        mocker.patch("koan.configurator.yum_available", True)
        yum_packages = mocker.patch.object(kc, "configure_yum_packages")

        # Act
        kc.configure_packages()

        # Assert
        yum_packages.assert_not_called()


class FakeStat:
    """Minimal stand-in for os.stat_result."""

    def __init__(self, mode, uid, gid):
        self.st_mode = mode
        self.st_uid = uid
        self.st_gid = gid


class TestConfigureDirectories:
    def _config(
        self, action, path="/tmp/some/dir", mode="0755", owner="user", group="group"
    ):
        return {
            "files": {
                "mydir": {
                    "is_dir": True,
                    "action": action,
                    "path": path,
                    "mode": mode,
                    "owner": owner,
                    "group": group,
                }
            }
        }

    def test_create_when_missing_creates_and_chowns(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=False)
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        makedirs = mocker.patch("koan.configurator.os.makedirs")
        chown = mocker.patch("koan.configurator.os.chown")
        chmod = mocker.patch("koan.configurator.os.chmod")

        # Act
        kc.configure_directories()

        # Assert
        makedirs.assert_called_once_with("/tmp/some/dir", 0o755)
        chown.assert_called_once_with("/tmp/some/dir", 1000, 1000)
        chmod.assert_not_called()
        assert kc.stats["dir"]["osync"] == 1
        assert kc.stats["dir"]["nsync"] == 0
        assert kc.stats["dir"]["fail"] == 0

    def test_create_when_exists_with_matching_owner_and_mode_is_noop(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=True)
        mocker.patch("koan.configurator.os.path.realpath", return_value="/tmp/some/dir")
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.pwd.getpwuid", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrgid", return_value=[None, None, 1000])
        mocker.patch(
            "koan.configurator.os.stat",
            return_value=FakeStat(stat_module.S_IFDIR | 0o755, 1000, 1000),
        )
        chown = mocker.patch("koan.configurator.os.chown")
        chmod = mocker.patch("koan.configurator.os.chmod")
        makedirs = mocker.patch("koan.configurator.os.makedirs")

        # Act
        kc.configure_directories()

        # Assert
        chown.assert_not_called()
        chmod.assert_not_called()
        makedirs.assert_not_called()
        assert kc.stats["dir"]["nsync"] == 1
        assert kc.stats["dir"]["osync"] == 0

    def test_create_when_exists_with_mismatched_mode_chmods_and_chowns(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=True)
        mocker.patch("koan.configurator.os.path.realpath", return_value="/tmp/some/dir")
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.pwd.getpwuid", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrgid", return_value=[None, None, 1000])
        mocker.patch(
            "koan.configurator.os.stat",
            return_value=FakeStat(stat_module.S_IFDIR | 0o700, 1000, 1000),
        )
        chown = mocker.patch("koan.configurator.os.chown")
        chmod = mocker.patch("koan.configurator.os.chmod")

        # Act
        kc.configure_directories()

        # Assert
        chmod.assert_called_once_with("/tmp/some/dir", 0o755)
        chown.assert_called_once_with("/tmp/some/dir", 1000, 1000)
        assert kc.stats["dir"]["osync"] == 1
        assert kc.stats["dir"]["nsync"] == 0

    def test_protected_directory_is_skipped(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create", path="/etc"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=True)
        mocker.patch("koan.configurator.os.path.realpath", return_value="/etc")
        makedirs = mocker.patch("koan.configurator.os.makedirs")
        chown = mocker.patch("koan.configurator.os.chown")
        chmod = mocker.patch("koan.configurator.os.chmod")

        # Act
        kc.configure_directories()

        # Assert
        makedirs.assert_not_called()
        chown.assert_not_called()
        chmod.assert_not_called()
        assert kc.stats["dir"]["fail"] == 1
        assert kc.stats["dir"]["osync"] == 0
        assert kc.stats["dir"]["nsync"] == 0

    def test_remove_when_exists_calls_rmtree(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("remove"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=True)
        mocker.patch("koan.configurator.os.path.realpath", return_value="/tmp/some/dir")
        rmtree = mocker.patch("koan.configurator.shutil.rmtree")

        # Act
        kc.configure_directories()

        # Assert
        rmtree.assert_called_once_with("/tmp/some/dir")
        assert kc.stats["dir"]["osync"] == 1
        assert kc.stats["dir"]["nsync"] == 0

    def test_remove_when_missing_is_noop(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("remove"))
        mocker.patch("koan.configurator.os.path.isdir", return_value=False)
        rmtree = mocker.patch("koan.configurator.shutil.rmtree")

        # Act
        kc.configure_directories()

        # Assert
        rmtree.assert_not_called()
        assert kc.stats["dir"]["nsync"] == 1
        assert kc.stats["dir"]["osync"] == 0


class TestConfigureFiles:
    def _config(
        self, action, path="/tmp/some/file", mode="0644", owner="user", group="group"
    ):
        return {
            "files": {
                "myfile": {
                    "is_dir": False,
                    "action": action,
                    "path": path,
                    "mode": mode,
                    "owner": owner,
                    "group": group,
                    "content": "hello world",
                }
            }
        }

    def test_create_when_missing_and_parent_dir_exists_syncs(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=False)
        mocker.patch("koan.configurator.os.path.dirname", return_value="/tmp/some")
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        tmp = mocker.patch("koan.configurator.tempfile.NamedTemporaryFile")
        tmp.return_value.name = "/tmp/tmpfile123"
        open_mock = mocker.patch("builtins.open", mocker.mock_open())
        sync_file = mocker.patch("koan.configurator.utils.sync_file")

        # Act
        kc.configure_files()

        # Assert
        open_mock.assert_called_once_with("/tmp/some/file", "w")
        sync_file.assert_called_once_with(
            "/tmp/some/file", "/tmp/tmpfile123", 1000, 1000, 0o644
        )
        assert kc.stats["files"]["osync"] == 1
        assert kc.stats["files"]["nsync"] == 0
        assert kc.stats["files"]["fail"] == 0

    def test_create_when_exists_and_differs_syncs(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=True)
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.pwd.getpwuid", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrgid", return_value=[None, None, 1000])
        mocker.patch(
            "koan.configurator.os.stat",
            return_value=FakeStat(stat_module.S_IFREG | 0o644, 1000, 1000),
        )
        tmp = mocker.patch("koan.configurator.tempfile.NamedTemporaryFile")
        tmp.return_value.name = "/tmp/tmpfile123"
        mocker.patch("koan.configurator.filecmp.cmp", return_value=False)
        sync_file = mocker.patch("koan.configurator.utils.sync_file")

        # Act
        kc.configure_files()

        # Assert
        sync_file.assert_called_once_with(
            "/tmp/some/file", "/tmp/tmpfile123", 1000, 1000, 0o644
        )
        assert kc.stats["files"]["osync"] == 1
        assert kc.stats["files"]["nsync"] == 0

    def test_create_when_exists_and_identical_is_noop(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=True)
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.pwd.getpwuid", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrgid", return_value=[None, None, 1000])
        mocker.patch(
            "koan.configurator.os.stat",
            return_value=FakeStat(stat_module.S_IFREG | 0o644, 1000, 1000),
        )
        tmp = mocker.patch("koan.configurator.tempfile.NamedTemporaryFile")
        tmp.return_value.name = "/tmp/tmpfile123"
        mocker.patch("koan.configurator.filecmp.cmp", return_value=True)
        sync_file = mocker.patch("koan.configurator.utils.sync_file")

        # Act
        kc.configure_files()

        # Assert
        sync_file.assert_not_called()
        assert kc.stats["files"]["nsync"] == 1
        assert kc.stats["files"]["osync"] == 0

    def test_create_when_missing_and_no_parent_dir_fails(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("create"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=False)
        mocker.patch("koan.configurator.os.path.dirname", return_value="")
        mocker.patch("koan.configurator.pwd.getpwnam", return_value=[None, None, 1000])
        mocker.patch("koan.configurator.grp.getgrnam", return_value=[None, None, 1000])
        tmp = mocker.patch("koan.configurator.tempfile.NamedTemporaryFile")
        tmp.return_value.name = "/tmp/tmpfile123"
        open_mock = mocker.patch("builtins.open", mocker.mock_open())
        sync_file = mocker.patch("koan.configurator.utils.sync_file")

        # Act
        kc.configure_files()

        # Assert
        open_mock.assert_not_called()
        sync_file.assert_not_called()
        assert kc.stats["files"]["fail"] == 1
        assert kc.stats["files"]["osync"] == 0
        assert kc.stats["files"]["nsync"] == 0

    def test_remove_when_exists_removes_file(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("remove"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=True)
        remove = mocker.patch("koan.configurator.os.remove")

        # Act
        kc.configure_files()

        # Assert
        remove.assert_called_once_with("/tmp/some/file")
        assert kc.stats["files"]["osync"] == 1
        assert kc.stats["files"]["nsync"] == 0

    def test_remove_when_missing_is_noop(self, mocker):
        # Arrange
        kc = make_configurator(mocker, self._config("remove"))
        mocker.patch("koan.configurator.os.path.isfile", return_value=False)
        remove = mocker.patch("koan.configurator.os.remove")

        # Act
        kc.configure_files()

        # Assert
        remove.assert_not_called()
        assert kc.stats["files"]["nsync"] == 1
        assert kc.stats["files"]["osync"] == 0


class TestRun:
    def test_run_calls_all_stages_and_returns_stats(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {"repos_enabled": True})
        repos = mocker.patch.object(kc, "configure_repos")
        packages = mocker.patch.object(kc, "configure_packages")
        directories = mocker.patch.object(kc, "configure_directories")
        files = mocker.patch.object(kc, "configure_files")
        kc.stats = {"marker": True}

        # Act
        result = kc.run()

        # Assert
        repos.assert_called_once()
        packages.assert_called_once()
        directories.assert_called_once()
        files.assert_called_once()
        assert result is kc.stats

    def test_run_skips_repos_when_disabled(self, mocker):
        # Arrange
        kc = make_configurator(mocker, {"repos_enabled": False})
        repos = mocker.patch.object(kc, "configure_repos")
        mocker.patch.object(kc, "configure_packages")
        mocker.patch.object(kc, "configure_directories")
        mocker.patch.object(kc, "configure_files")

        # Act
        kc.run()

        # Assert
        repos.assert_not_called()
