"""ollama-ctl: CLI utility for managing Ollama servers."""

__version__ = "0.1.0"
__author__ = "James Radtke"
__email__ = "james@radtke.io"

from ollama_ctl.client import OllamaClient
from ollama_ctl.config import Config, HostConfig

__all__ = ["OllamaClient", "Config", "HostConfig", "__version__"]
