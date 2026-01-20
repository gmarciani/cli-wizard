# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for config commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from cli_wizard.commands.config import config


class TestConfigCommands:
    """Tests for config command group."""

    def test_config_group_exists(self):
        """Test config command group exists."""
        runner = CliRunner()
        result = runner.invoke(config, ["--help"])
        assert result.exit_code == 0
        assert "Manage configurations" in result.output

    def test_config_set(self):
        """Test config set command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            with patch(
                "cli_wizard.commands.config.get_config_path",
                return_value=config_path,
            ):
                with patch(
                    "cli_wizard.commands.config.load_config",
                    return_value={"existing": "value"},
                ):
                    with patch("cli_wizard.commands.config.save_config") as mock_save:
                        result = runner.invoke(config, ["set", "key", "value"])
                        assert result.exit_code == 0
                        output = json.loads(result.output)
                        assert output["key"] == "key"
                        assert output["value"] == "value"
                        mock_save.assert_called_once()

    def test_config_get(self):
        """Test config get command."""
        runner = CliRunner()
        with patch(
            "cli_wizard.commands.config.load_config",
            return_value={"mykey": "myvalue"},
        ):
            result = runner.invoke(config, ["get", "mykey"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["key"] == "mykey"
            assert output["value"] == "myvalue"

    def test_config_get_unknown_key(self):
        """Test config get with unknown key."""
        runner = CliRunner()
        with patch(
            "cli_wizard.commands.config.load_config",
            return_value={"other": "value"},
        ):
            result = runner.invoke(config, ["get", "unknown"])
            assert result.exit_code == 0
            # Should log error but not crash

    def test_config_unset(self):
        """Test config unset command."""
        runner = CliRunner()
        with patch(
            "cli_wizard.commands.config.load_config",
            return_value={"mykey": "myvalue"},
        ):
            with patch("cli_wizard.commands.config.save_config") as mock_save:
                result = runner.invoke(config, ["unset", "mykey"])
                assert result.exit_code == 0
                output = json.loads(result.output)
                assert output["key"] == "mykey"
                assert output["value"] is None
                assert output["oldValue"] == "myvalue"
                mock_save.assert_called_once()

    def test_config_unset_unknown_key(self):
        """Test config unset with unknown key."""
        runner = CliRunner()
        with patch(
            "cli_wizard.commands.config.load_config",
            return_value={"other": "value"},
        ):
            result = runner.invoke(config, ["unset", "unknown"])
            assert result.exit_code == 0
            # Should log error but not crash

    def test_config_show(self):
        """Test config show command."""
        runner = CliRunner()
        test_config = {"key1": "value1", "key2": "value2"}
        with patch(
            "cli_wizard.commands.config.load_config",
            return_value=test_config,
        ):
            result = runner.invoke(config, ["show"])
            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output == test_config

    def test_config_reset(self):
        """Test config reset command."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("key: value")

            with patch(
                "cli_wizard.commands.config.get_config_path",
                return_value=config_path,
            ):
                with patch(
                    "cli_wizard.commands.config.load_config",
                    return_value={"default": "config"},
                ):
                    result = runner.invoke(config, ["reset"])
                    assert result.exit_code == 0
                    # Config file should be deleted
                    assert not config_path.exists()

    def test_config_reset_no_file(self):
        """Test config reset when no config file exists."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            # Don't create the file

            with patch(
                "cli_wizard.commands.config.get_config_path",
                return_value=config_path,
            ):
                with patch(
                    "cli_wizard.commands.config.load_config",
                    return_value={"default": "config"},
                ):
                    result = runner.invoke(config, ["reset"])
                    assert result.exit_code == 0
