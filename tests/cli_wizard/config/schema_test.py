# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration schema."""

import pytest
from pydantic import ValidationError

from cli_wizard.config.schema import Config


class TestConfigSchema:
    """Tests for Config schema validation."""

    def test_minimal_valid_config(self):
        """Test minimal valid configuration with only required fields."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
        )
        assert config.PackageName == "my-cli"
        assert config.DefaultBaseUrl == "https://api.example.com"
        assert config.OutputDir == "#[PackageName]"
        assert config.Timeout == 30

    def test_missing_package_name(self):
        """Test that PackageName is required."""
        with pytest.raises(ValidationError) as exc_info:
            Config(DefaultBaseUrl="https://api.example.com")
        assert "PackageName" in str(exc_info.value)

    def test_missing_default_base_url(self):
        """Test that DefaultBaseUrl is required."""
        with pytest.raises(ValidationError) as exc_info:
            Config(PackageName="my-cli")
        assert "DefaultBaseUrl" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                UnknownField="value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_valid_hex_color(self):
        """Test valid hex color codes."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
            SplashColor="#FF0000",
            LogColorDebug="#00FF00",
        )
        assert config.SplashColor == "#FF0000"
        assert config.LogColorDebug == "#00FF00"

    def test_invalid_hex_color(self):
        """Test invalid hex color codes."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                SplashColor="red",
            )
        assert "Invalid hex color code" in str(exc_info.value)

    def test_invalid_hex_color_short(self):
        """Test invalid short hex color codes."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                SplashColor="#FFF",
            )
        assert "Invalid hex color code" in str(exc_info.value)

    def test_hex_color_normalized_to_uppercase(self):
        """Test that hex colors are normalized to uppercase."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
            SplashColor="#aabbcc",
        )
        assert config.SplashColor == "#AABBCC"

    def test_default_values(self):
        """Test default values are set correctly."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
        )
        assert config.OutputDir == "#[PackageName]"
        assert config.MainDir == "${HOME}/.#[PackageName]"
        assert config.ProfileFile == "#[MainDir]/profiles.yaml"
        assert config.ExcludeTags == []
        assert config.IncludeTags == []
        assert config.TagMapping == {}
        assert config.OutputFormat == "json"
        assert config.Timeout == 30
        assert config.LogLevel == "INFO"
        assert config.LogFile is None
        assert config.SplashFile is None
        assert config.CaFile is None

    def test_log_level_validation(self):
        """Test log level validation."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
            LogLevel="DEBUG",
        )
        assert config.LogLevel == "DEBUG"

        with pytest.raises(ValidationError):
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                LogLevel="INVALID",
            )

    def test_output_format_validation(self):
        """Test output format validation."""
        for fmt in ["json", "table", "yaml"]:
            config = Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                OutputFormat=fmt,
            )
            assert config.OutputFormat == fmt

        with pytest.raises(ValidationError):
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                OutputFormat="xml",
            )

    def test_timeout_validation(self):
        """Test timeout must be positive."""
        with pytest.raises(ValidationError):
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                Timeout=0,
            )

    def test_json_indent_validation(self):
        """Test JSON indent must be non-negative."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
            JsonIndent=0,
        )
        assert config.JsonIndent == 0

        with pytest.raises(ValidationError):
            Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                JsonIndent=-1,
            )

    def test_log_rotation_type_validation(self):
        """Test log rotation type validation."""
        for rotation_type in ["size", "days"]:
            config = Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                LogRotationType=rotation_type,
            )
            assert config.LogRotationType == rotation_type

    def test_table_style_validation(self):
        """Test table style validation."""
        for style in ["ascii", "rounded", "minimal", "markdown"]:
            config = Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                TableStyle=style,
            )
            assert config.TableStyle == style

    def test_log_color_style_validation(self):
        """Test log color style validation."""
        for style in ["full", "level"]:
            config = Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                LogColorStyle=style,
            )
            assert config.LogColorStyle == style

    def test_log_timezone_validation(self):
        """Test log timezone validation."""
        for tz in ["UTC", "Local"]:
            config = Config(
                PackageName="my-cli",
                DefaultBaseUrl="https://api.example.com",
                LogTimezone=tz,
            )
            assert config.LogTimezone == tz

    def test_full_config(self):
        """Test full configuration with all fields."""
        config = Config(
            PackageName="my-cli",
            DefaultBaseUrl="https://api.example.com",
            OutputDir="output",
            MainDir="/home/user/.my-cli",
            ProfileFile="/home/user/.my-cli/profiles.yaml",
            OpenapiSpec="api.yaml",
            ExcludeTags=["internal"],
            IncludeTags=["public"],
            TagMapping={"Users": "user-management"},
            CommandMapping={"listUsers": "list"},
            OutputFormat="table",
            OutputColors=False,
            JsonIndent=4,
            TableStyle="markdown",
            SplashFile="splash.txt",
            SplashColor="#00FFFF",
            LogLevel="DEBUG",
            LogFormat="%(message)s",
            LogTimestampFormat="%H:%M:%S",
            LogTimezone="Local",
            LogColorStyle="full",
            LogColorDebug="#AAAAAA",
            LogColorInfo="#00FF00",
            LogColorWarning="#FFFF00",
            LogColorError="#FF0000",
            LogFile="/var/log/my-cli.log",
            LogRotationType="size",
            LogRotationSize=50,
            LogRotationDays=7,
            LogRotationBackupCount=10,
            Timeout=60,
            CaFile="/etc/ssl/certs/ca.pem",
            RetryMaxAttempts=5,
            RetryBackoffFactor=1.0,
        )
        assert config.PackageName == "my-cli"
        assert config.ExcludeTags == ["internal"]
        assert config.LogRotationSize == 50
