"""Tests for configuration module."""

from rdf4j_mcp.config import BackendType, Settings, configure, get_settings


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.backend_type == BackendType.LOCAL
        assert settings.rdf4j_server_url == "http://localhost:8080/rdf4j-server"
        assert settings.default_repository is None
        assert settings.local_store_path is None
        assert settings.local_store_format == "turtle"
        assert settings.query_timeout == 30
        assert settings.default_limit == 100
        assert settings.max_limit == 10000
        assert settings.server_name == "rdf4j-mcp"
        assert settings.server_version == "0.1.0"

    def test_custom_settings(self):
        """Test custom settings values."""
        settings = Settings(
            backend_type=BackendType.REMOTE,
            rdf4j_server_url="http://custom:9999/rdf4j",
            default_repository="test-repo",
            query_timeout=60,
            default_limit=50,
        )

        assert settings.backend_type == BackendType.REMOTE
        assert settings.rdf4j_server_url == "http://custom:9999/rdf4j"
        assert settings.default_repository == "test-repo"
        assert settings.query_timeout == 60
        assert settings.default_limit == 50

    def test_backend_type_enum(self):
        """Test BackendType enum values."""
        assert BackendType.LOCAL.value == "local"
        assert BackendType.REMOTE.value == "remote"

    def test_settings_from_env(self, monkeypatch):
        """Test settings from environment variables."""
        monkeypatch.setenv("RDF4J_MCP_BACKEND_TYPE", "remote")
        monkeypatch.setenv("RDF4J_MCP_RDF4J_SERVER_URL", "http://env-server:8080")
        monkeypatch.setenv("RDF4J_MCP_DEFAULT_REPOSITORY", "env-repo")
        monkeypatch.setenv("RDF4J_MCP_QUERY_TIMEOUT", "45")

        settings = Settings()

        assert settings.backend_type == BackendType.REMOTE
        assert settings.rdf4j_server_url == "http://env-server:8080"
        assert settings.default_repository == "env-repo"
        assert settings.query_timeout == 45


class TestGlobalSettings:
    """Test global settings management."""

    def test_get_settings_returns_instance(self):
        """Test get_settings returns a Settings instance."""
        # Reset global settings
        import rdf4j_mcp.config as config_module

        config_module._settings = None

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_configure_sets_global(self):
        """Test configure sets global settings."""
        import rdf4j_mcp.config as config_module

        config_module._settings = None

        custom = Settings(query_timeout=99)
        configure(custom)

        settings = get_settings()
        assert settings.query_timeout == 99

        # Reset for other tests
        config_module._settings = None

    def test_get_settings_caches(self):
        """Test get_settings caches the instance."""
        import rdf4j_mcp.config as config_module

        config_module._settings = None

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

        # Reset for other tests
        config_module._settings = None
