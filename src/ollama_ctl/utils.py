"""Utility functions for ollama-ctl."""

from typing import Optional, Tuple
from rich.table import Table
from rich.console import Console

from ollama_ctl.models import ModelInfo


def parse_host_arg(host: Optional[str]) -> Tuple[str, Optional[int]]:
    """Parse host argument into hostname and port.

    Handles formats:
    - "hostname" -> ("hostname", None)
    - "hostname:port" -> ("hostname", port)
    - "192.168.1.100" -> ("192.168.1.100", None)
    - "192.168.1.100:8080" -> ("192.168.1.100", 8080)

    Args:
        host: Host string (alias, hostname, or hostname:port)

    Returns:
        Tuple of (hostname, port) where port may be None
    """
    if not host:
        return ("localhost", None)

    if ":" in host:
        hostname, port_str = host.rsplit(":", 1)
        try:
            port = int(port_str)
            return (hostname, port)
        except ValueError:
            # Not a valid port, treat entire string as hostname
            return (host, None)

    return (host, None)


def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.23 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def create_models_table(models: list[ModelInfo], title: str = "Available Models") -> Table:
    """Create a rich Table for displaying models.

    Args:
        models: List of ModelInfo objects
        title: Table title

    Returns:
        Configured Table object
    """
    table = Table(title=title)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Size", style="green")
    table.add_column("Modified", style="blue")

    for model in models:
        size_str = format_bytes(model.size)
        table.add_row(model.get_name(), size_str, model.modified_at)

    return table


def format_duration(microseconds: Optional[int]) -> str:
    """Format duration in microseconds to human-readable string.

    Args:
        microseconds: Duration in microseconds

    Returns:
        Formatted string (e.g., "1.23s", "456ms")
    """
    if microseconds is None:
        return "N/A"

    if microseconds < 1000:
        return f"{microseconds}µs"
    elif microseconds < 1_000_000:
        ms = microseconds / 1000
        return f"{ms:.1f}ms"
    else:
        seconds = microseconds / 1_000_000
        if seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"


def validate_model_name(name: str) -> bool:
    """Validate model name format.

    Model names should be lowercase alphanumeric with hyphens and colons.

    Args:
        name: Model name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    # Basic validation: alphanumeric, hyphens, colons, dots, underscores
    import re

    pattern = r"^[a-z0-9._:/-]+$"
    return bool(re.match(pattern, name.lower()))


def truncate_string(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate string to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
