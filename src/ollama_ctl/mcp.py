"""MCP (Model Context Protocol) integration for ollama-ctl."""

import json
from pathlib import Path
from typing import Optional
import re

from ollama_ctl.models import Config, HostConfig


class MCPConfig:
    """Handler for MCP configuration files."""

    def __init__(self, config_data: dict):
        """Initialize with parsed MCP config data.

        Args:
            config_data: Parsed MCP configuration dictionary
        """
        self.config_data = config_data
        self.mcp_servers = config_data.get("mcpServers", {})

    @classmethod
    def from_file(cls, config_path: Path) -> "MCPConfig":
        """Load MCP config from a file.

        Args:
            config_path: Path to MCP configuration file

        Returns:
            MCPConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"MCP config not found: {config_path}")

        with open(config_path) as f:
            data = json.load(f)

        return cls(data)

    def extract_ollama_hosts(self) -> dict[str, HostConfig]:
        """Extract Ollama server configurations from MCP config.

        Looks for servers that:
        - Have 'ollama' in their name
        - Use 'ollama' command
        - Have OLLAMA_HOST environment variable

        Returns:
            Dictionary mapping host aliases to HostConfig objects
        """
        hosts = {}

        for server_name, server_config in self.mcp_servers.items():
            # Check if this server is related to Ollama
            command = server_config.get("command", "")
            env = server_config.get("env", {})

            is_ollama_server = (
                "ollama" in server_name.lower()
                or "ollama" in command.lower()
                or "OLLAMA_HOST" in env
            )

            if not is_ollama_server:
                continue

            # Extract host configuration
            host_config = self._parse_ollama_env(env)
            if host_config:
                # Use server name as alias (sanitize for use as alias)
                alias = self._sanitize_alias(server_name)
                hosts[alias] = host_config

        return hosts

    def _parse_ollama_env(self, env: dict) -> Optional[HostConfig]:
        """Parse Ollama host configuration from environment variables.

        Args:
            env: Environment variables dictionary

        Returns:
            HostConfig if Ollama configuration found, None otherwise
        """
        ollama_host = env.get("OLLAMA_HOST")
        if not ollama_host:
            return None

        # Remove protocol if present
        protocol = "http"
        if ollama_host.startswith("https://"):
            protocol = "https"
            ollama_host = ollama_host[8:]
        elif ollama_host.startswith("http://"):
            protocol = "http"
            ollama_host = ollama_host[7:]

        # Parse hostname:port
        hostname = ollama_host
        port = 11434  # default

        if ":" in ollama_host:
            hostname, port_str = ollama_host.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                # If port is not a number, keep default
                hostname = ollama_host

        return HostConfig(hostname=hostname, port=port, protocol=protocol)

    @staticmethod
    def _sanitize_alias(name: str) -> str:
        """Sanitize server name for use as host alias.

        Converts to lowercase, replaces spaces and special chars with hyphens.

        Args:
            name: Original server name

        Returns:
            Sanitized alias
        """
        # Convert to lowercase
        alias = name.lower()

        # Replace spaces and underscores with hyphens
        alias = alias.replace(" ", "-").replace("_", "-")

        # Remove non-alphanumeric characters except hyphens
        alias = re.sub(r"[^a-z0-9-]", "", alias)

        # Remove duplicate hyphens
        alias = re.sub(r"-+", "-", alias)

        # Remove leading/trailing hyphens
        alias = alias.strip("-")

        return alias


def find_mcp_config() -> Optional[Path]:
    """Find MCP configuration file in standard locations.

    Checks (in order):
    1. .cursor/mcp.json (project-specific, Cursor editor)
    2. ~/.cursor/mcp.json (global Cursor config)
    3. ~/Library/Application Support/Claude/claude_desktop_config.json (macOS Claude Desktop)
    4. ~/.config/Claude/claude_desktop_config.json (Linux Claude Desktop)

    Returns:
        Path to MCP config if found, None otherwise
    """
    # Project-specific Cursor config
    project_mcp = Path.cwd() / ".cursor" / "mcp.json"
    if project_mcp.exists():
        return project_mcp

    # Global Cursor config
    home = Path.home()
    global_cursor = home / ".cursor" / "mcp.json"
    if global_cursor.exists():
        return global_cursor

    # Claude Desktop configs (macOS)
    if Path("/Users").exists():  # macOS
        claude_macos = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if claude_macos.exists():
            return claude_macos

    # Claude Desktop configs (Linux)
    claude_linux = home / ".config" / "Claude" / "claude_desktop_config.json"
    if claude_linux.exists():
        return claude_linux

    return None


def load_mcp_config(config_path: Optional[Path] = None) -> Optional[MCPConfig]:
    """Load MCP configuration from file.

    Args:
        config_path: Optional path to MCP config file.
                    If not provided, searches standard locations.

    Returns:
        MCPConfig instance if found, None otherwise
    """
    if config_path is None:
        config_path = find_mcp_config()

    if config_path is None:
        return None

    try:
        return MCPConfig.from_file(config_path)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def merge_mcp_hosts(config: Config, mcp_hosts: dict[str, HostConfig]) -> Config:
    """Merge MCP hosts into existing configuration.

    MCP hosts are added to the config with their aliases.
    Existing hosts with the same alias are NOT overwritten.

    Args:
        config: Existing Config object
        mcp_hosts: Dictionary of MCP host configurations

    Returns:
        New Config object with merged hosts
    """
    # Create a copy of the config data
    config_data = config.model_dump()

    # Merge hosts (don't overwrite existing)
    for alias, host_config in mcp_hosts.items():
        if alias not in config_data["hosts"]:
            config_data["hosts"][alias] = host_config.model_dump()

    return Config(**config_data)


def create_example_mcp_config(output_path: Path) -> None:
    """Create an example MCP configuration file.

    Args:
        output_path: Path where to write the example config
    """
    example_config = {
        "mcpServers": {
            "ollama-local": {
                "command": "ollama",
                "args": ["serve"],
                "env": {"OLLAMA_HOST": "localhost:11434"},
            },
            "ollama-remote": {
                "command": "ssh",
                "args": ["user@remote", "ollama", "serve"],
                "env": {"OLLAMA_HOST": "https://192.168.1.100:11434"},
            },
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(example_config, f, indent=2)
