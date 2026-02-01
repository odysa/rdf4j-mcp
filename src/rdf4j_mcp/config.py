"""Configuration for RDF4J MCP Server."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="RDF4J_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Remote backend settings (RDF4J Server)
    rdf4j_server_url: str = Field(
        default="http://localhost:8080/rdf4j-server",
        description="URL of the RDF4J server",
    )
    default_repository: str | None = Field(
        default=None,
        description="Default repository ID to use",
    )

    # Query settings
    query_timeout: int = Field(
        default=30,
        description="Query timeout in seconds",
    )
    default_limit: int = Field(
        default=100,
        description="Default LIMIT for queries without explicit limit",
    )
    max_limit: int = Field(
        default=10000,
        description="Maximum allowed LIMIT for queries",
    )

    # Server settings
    server_name: str = Field(
        default="rdf4j-mcp",
        description="Name of the MCP server",
    )
    server_version: str = Field(
        default="0.1.0",
        description="Version of the MCP server",
    )
    readonly: bool = Field(
        default=False,
        description="Block write operations (INSERT, DELETE, UPDATE, etc.)",
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def configure(settings: Settings) -> None:
    """Configure the server with custom settings."""
    global _settings
    _settings = settings
