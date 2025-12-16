"""Configuration management for ollama-ctl."""

import os
from pathlib import Path
from typing import Optional

import yaml
from platformdirs import user_config_dir
from pydantic import ValidationError

from ollama_ctl.models import Config, HostConfig


def get_default_config_path() -> Path:
    """Get the default configuration file path.

    Returns the path to the user's config file in the appropriate
    platform-specific config directory.
    """
    config_dir = Path(user_config_dir("ollama-ctl", appauthor=False))
    return config_dir / "config.yaml"


def get_config_paths() -> list[Path]:
    """Get list of configuration file paths to check, in priority order.

    Priority:
    1. Local config (./.ollama-ctl.yaml)
    2. Global config (~/.config/ollama-ctl/config.yaml or platform equivalent)
    """
    paths = []

    # Local config in current directory
    local_config = Path.cwd() / ".ollama-ctl.yaml"
    if local_config.exists():
        paths.append(local_config)

    # Global config in user's config directory
    global_config = get_default_config_path()
    if global_config.exists():
        paths.append(global_config)

    return paths


def load_config_file(config_path: Path) -> dict:
    """Load and parse a YAML configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Parsed configuration as a dictionary

    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return data or {}


def merge_configs(base_config: dict, override_config: dict) -> dict:
    """Merge two configuration dictionaries.

    Args:
        base_config: Base configuration
        override_config: Configuration to override base with

    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file(s) and environment variables.

    Configuration priority (highest to lowest):
    1. Environment variables (OLLAMA_HOST, OLLAMA_PORT)
    2. Specified config file path
    3. Local config file (./.ollama-ctl.yaml)
    4. Global config file (~/.config/ollama-ctl/config.yaml)
    5. Defaults

    Args:
        config_path: Optional path to a specific config file

    Returns:
        Validated Config object

    Raises:
        ValidationError: If configuration is invalid
    """
    config_data = {}

    # Load from config files
    if config_path:
        # If specific config path is provided, use only that
        try:
            config_data = load_config_file(config_path)
        except FileNotFoundError:
            raise
    else:
        # Otherwise, merge configs from all standard locations
        for path in reversed(get_config_paths()):  # Reverse to get correct priority
            try:
                file_config = load_config_file(path)
                config_data = merge_configs(config_data, file_config)
            except FileNotFoundError:
                continue

    # Apply environment variable overrides
    env_overrides = get_env_overrides()
    if env_overrides:
        config_data = merge_configs(config_data, env_overrides)

    # If no config found anywhere, use defaults
    if not config_data:
        return Config()

    try:
        return Config(**config_data)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration: {e}")


def get_env_overrides() -> dict:
    """Get configuration overrides from environment variables.

    Supports:
    - OLLAMA_HOST: hostname or hostname:port
    - OLLAMA_PORT: port number
    - OLLAMA_PROTOCOL: http or https

    Returns:
        Dictionary with environment variable overrides
    """
    overrides = {}

    ollama_host = os.environ.get("OLLAMA_HOST")
    if ollama_host:
        host_config: dict = {}

        # Parse host:port format
        if ":" in ollama_host:
            hostname, port_str = ollama_host.rsplit(":", 1)
            try:
                host_config["hostname"] = hostname
                host_config["port"] = int(port_str)
            except ValueError:
                # Not a valid port, treat entire string as hostname
                host_config["hostname"] = ollama_host
        else:
            host_config["hostname"] = ollama_host

        # Override with OLLAMA_PORT if set
        ollama_port = os.environ.get("OLLAMA_PORT")
        if ollama_port:
            try:
                host_config["port"] = int(ollama_port)
            except ValueError:
                pass

        # Override with OLLAMA_PROTOCOL if set
        ollama_protocol = os.environ.get("OLLAMA_PROTOCOL")
        if ollama_protocol and ollama_protocol in ("http", "https"):
            host_config["protocol"] = ollama_protocol

        # Add as 'env' host and make it default
        if host_config:
            overrides["hosts"] = {"env": host_config}
            overrides["default_host"] = "env"

    return overrides


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to a YAML file.

    Args:
        config: Config object to save
        config_path: Path to save to (defaults to global config)
    """
    if config_path is None:
        config_path = get_default_config_path()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and write as YAML
    config_data = config.model_dump(exclude_defaults=False)

    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)


def create_example_config(output_path: Path) -> None:
    """Create an example configuration file.

    Args:
        output_path: Path where to write the example config
    """
    example_config = Config(
        default_host="local",
        hosts={
            "local": HostConfig(hostname="localhost", port=11434, protocol="http"),
            "remote": HostConfig(
                hostname="192.168.1.100", port=11434, protocol="https", verify_ssl=True
            ),
            "cloud": HostConfig(
                hostname="ollama.example.com", port=443, protocol="https", verify_ssl=True
            ),
        },
        settings={
            "timeout": 30,
            "stream": True,
            "default_model": "llama2",
        },
    )

    save_config(example_config, output_path)
