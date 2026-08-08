# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration schema."""

from datetime import date

import pytest
from pydantic import ValidationError

from cli_wizard.config.schema import Config


class TestConfigSchema:
    """Tests for Config schema validation."""

    def test_minimal_valid_config(self):
        """Test minimal valid configuration uses defaults."""
        config = Config()
        assert config.PackageName == "my_project"
        assert config.DefaultBaseUrl == "http://localhost:3000"
        assert config.MainDir == "${HOME}/.#[CommandName]"
        assert config.Timeout == 30

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = Config(
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
        )
        assert config.PackageName == "my_cli"
        assert config.DefaultBaseUrl == "https://api.example.com"

    @pytest.mark.parametrize(
        "package_name",
        ["my-cli", "my cli", "2cli", "my.cli", "class"],
    )
    def test_invalid_package_name_rejected(self, package_name):
        """Test that PackageName must be a valid Python package name."""
        with pytest.raises(ValidationError) as exc_info:
            Config(PackageName=package_name)
        assert "not a valid Python package name" in str(exc_info.value)

    @pytest.mark.parametrize("package_name", ["my_cli", "mycli", "my_cli2", "_cli"])
    def test_valid_package_name_accepted(self, package_name):
        """Test that valid Python identifiers are accepted as PackageName."""
        assert Config(PackageName=package_name).PackageName == package_name

    def test_empty_package_name_falls_back_to_derivation(self):
        """Test that an empty PackageName is derived from ProjectName."""
        assert Config(PackageName="", ProjectName="My CLI").PackageName == "my_cli"

    def test_copyright_year_defaults_to_current_year(self):
        """Test that CopyrightYear defaults to the current year."""
        assert Config().CopyrightYear == date.today().year

    def test_copyright_year_explicit_value_kept(self):
        """Test that an explicit CopyrightYear is preserved."""
        assert Config(CopyrightYear=2019).CopyrightYear == 2019

    def test_repository_url_derived_from_github_user_and_command(self):
        """Test that RepositoryUrl is derived when not set."""
        config = Config(ProjectName="My Cli", GithubUser="someone")
        assert config.RepositoryUrl == "https://github.com/someone/my-cli"

    def test_repository_url_explicit_value_kept(self):
        """Test that an explicit RepositoryUrl is preserved."""
        config = Config(GithubUser="someone", RepositoryUrl="https://example.com/x")
        assert config.RepositoryUrl == "https://example.com/x"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                UnknownField="value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_valid_hex_color(self):
        """Test valid hex color codes."""
        config = Config(
            PackageName="my_cli",
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
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                SplashColor="red",
            )
        assert "Invalid hex color code" in str(exc_info.value)

    def test_invalid_hex_color_short(self):
        """Test invalid short hex color codes."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                SplashColor="#FFF",
            )
        assert "Invalid hex color code" in str(exc_info.value)

    def test_hex_color_normalized_to_uppercase(self):
        """Test that hex colors are normalized to uppercase."""
        config = Config(
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
            SplashColor="#aabbcc",
        )
        assert config.SplashColor == "#AABBCC"

    def test_default_values(self):
        """Test default values are set correctly."""
        config = Config(
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
        )
        assert config.MainDir == "${HOME}/.#[CommandName]"
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
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
            LogLevel="DEBUG",
        )
        assert config.LogLevel == "DEBUG"

        with pytest.raises(ValidationError):
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                LogLevel="INVALID",
            )

    def test_output_format_validation(self):
        """Test output format validation."""
        for fmt in ["json", "table", "yaml"]:
            config = Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                OutputFormat=fmt,
            )
            assert config.OutputFormat == fmt

        with pytest.raises(ValidationError):
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                OutputFormat="xml",
            )

    def test_timeout_validation(self):
        """Test timeout must be positive."""
        with pytest.raises(ValidationError):
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                Timeout=0,
            )

    def test_json_indent_validation(self):
        """Test JSON indent must be non-negative."""
        config = Config(
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
            JsonIndent=0,
        )
        assert config.JsonIndent == 0

        with pytest.raises(ValidationError):
            Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                JsonIndent=-1,
            )

    def test_log_rotation_type_validation(self):
        """Test log rotation type validation."""
        for rotation_type in ["size", "days"]:
            config = Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                LogRotationType=rotation_type,
            )
            assert config.LogRotationType == rotation_type

    def test_table_style_validation(self):
        """Test table style validation."""
        for style in ["ascii", "rounded", "minimal", "markdown"]:
            config = Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                TableStyle=style,
            )
            assert config.TableStyle == style

    def test_log_color_style_validation(self):
        """Test log color style validation."""
        for style in ["full", "level"]:
            config = Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                LogColorStyle=style,
            )
            assert config.LogColorStyle == style

    def test_log_timezone_validation(self):
        """Test log timezone validation."""
        for tz in ["UTC", "Local"]:
            config = Config(
                PackageName="my_cli",
                DefaultBaseUrl="https://api.example.com",
                LogTimezone=tz,
            )
            assert config.LogTimezone == tz

    def test_full_config(self):
        """Test full configuration with all fields."""
        config = Config(
            PackageName="my_cli",
            DefaultBaseUrl="https://api.example.com",
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
        assert config.PackageName == "my_cli"
        assert config.ExcludeTags == ["internal"]
        assert config.LogRotationSize == 50


class TestParseCliValue:
    """Tests for Config.parse_cli_value."""

    @pytest.mark.parametrize(
        "field_name,raw",
        [
            ("ProjectName", "My Project"),
            ("JsonIndent", "4"),
            ("OutputColors", "false"),
            ("CommandName", "my-cli"),
            ("LogFile", "/var/log/my-cli.log"),
        ],
    )
    def test_scalars_pass_through_untouched(self, field_name, raw):
        """Scalars are left for Pydantic to coerce."""
        assert Config.parse_cli_value(field_name, raw) == raw

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("users", ["users"]),
            ("users,admin", ["users", "admin"]),
            ("users, admin", ["users", "admin"]),
            ("users,,admin", ["users", "admin"]),
            ("users,", ["users"]),
            ("  users  ", ["users"]),
            ("", []),
            (",", []),
        ],
    )
    def test_list_fields_split_on_commas(self, raw, expected):
        """List fields accept a comma-separated string."""
        assert Config.parse_cli_value("IncludeTags", raw) == expected

    @pytest.mark.parametrize("field_name", ["TagMapping", "CommandMapping"])
    def test_mapping_fields_are_rejected(self, field_name):
        """Mappings have no single-argument form and are rejected outright."""
        with pytest.raises(ValueError, match="mapping and cannot be set"):
            Config.parse_cli_value(field_name, "a=b")

    def test_unknown_field_is_rejected(self):
        """An unknown field name is an error, not a silent pass-through."""
        with pytest.raises(ValueError, match="not a configuration key"):
            Config.parse_cli_value("NotAField", "value")


class TestDeriveNamesFromProject:
    """Tests for derivation robustness."""

    def test_explicit_null_project_name_is_a_validation_error(self):
        """A null ProjectName must not reach re.sub and raise TypeError."""
        with pytest.raises(ValidationError):
            Config(ProjectName=None)
