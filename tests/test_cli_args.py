"""Tests for CLI argument parsing."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

from rdf4j_mcp.config import BackendType, Settings
from rdf4j_mcp.server import main


class TestCLIArguments:
    """Test command line argument parsing."""

    def test_server_url_required(self, monkeypatch, capsys):
        """Test that server_url is required."""
        monkeypatch.setattr(sys, "argv", ["rdf4j-mcp"])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "server_url is required" in captured.err

    @patch("rdf4j_mcp.server.create_server")
    @patch("asyncio.run")
    def test_server_url_positional(self, mock_asyncio_run, mock_create_server, monkeypatch):
        """Test server_url as positional argument."""
        mock_server = AsyncMock()
        mock_create_server.return_value = mock_server

        test_url = "http://test-server:8080/rdf4j-server"
        monkeypatch.setattr(sys, "argv", ["rdf4j-mcp", test_url])

        try:
            main()
        except SystemExit:
            pass

        # Check that create_server was called with correct settings
        assert mock_create_server.called
        settings = mock_create_server.call_args[0][0]
        assert isinstance(settings, Settings)
        assert settings.backend_type == BackendType.REMOTE
        assert settings.rdf4j_server_url == test_url
        assert settings.default_repository is None

    @patch("rdf4j_mcp.server.create_server")
    @patch("asyncio.run")
    def test_server_url_with_repository(
        self, mock_asyncio_run, mock_create_server, monkeypatch
    ):
        """Test server_url with repository option."""
        mock_server = AsyncMock()
        mock_create_server.return_value = mock_server

        test_url = "http://test-server:8080/rdf4j-server"
        test_repo = "my-test-repo"
        monkeypatch.setattr(
            sys, "argv", ["rdf4j-mcp", test_url, "--repository", test_repo]
        )

        try:
            main()
        except SystemExit:
            pass

        # Check that create_server was called with correct settings
        assert mock_create_server.called
        settings = mock_create_server.call_args[0][0]
        assert isinstance(settings, Settings)
        assert settings.backend_type == BackendType.REMOTE
        assert settings.rdf4j_server_url == test_url
        assert settings.default_repository == test_repo

    @patch("rdf4j_mcp.server.create_server")
    @patch("asyncio.run")
    def test_debug_flag(self, mock_asyncio_run, mock_create_server, monkeypatch):
        """Test debug flag."""
        mock_server = AsyncMock()
        mock_create_server.return_value = mock_server

        test_url = "http://test-server:8080/rdf4j-server"
        monkeypatch.setattr(sys, "argv", ["rdf4j-mcp", test_url, "--debug"])

        import logging

        try:
            main()
        except SystemExit:
            pass

        # Check that debug logging was enabled
        assert logging.getLogger().level == logging.DEBUG

    def test_always_uses_remote_backend(self, monkeypatch):
        """Test that the backend is always set to REMOTE."""
        with patch("rdf4j_mcp.server.create_server") as mock_create_server, patch(
            "asyncio.run"
        ):
            mock_server = AsyncMock()
            mock_create_server.return_value = mock_server

            test_url = "http://test-server:8080/rdf4j-server"
            monkeypatch.setattr(sys, "argv", ["rdf4j-mcp", test_url])

            try:
                main()
            except SystemExit:
                pass

            # Verify remote backend is always used
            settings = mock_create_server.call_args[0][0]
            assert settings.backend_type == BackendType.REMOTE
