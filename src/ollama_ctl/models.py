"""Pydantic data models for Ollama API requests and responses."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class HostConfig(BaseModel):
    """Configuration for an Ollama host."""

    hostname: str
    port: int = 11434
    protocol: str = "http"
    verify_ssl: bool = True

    def get_base_url(self) -> str:
        """Get the base URL for this host."""
        return f"{self.protocol}://{self.hostname}:{self.port}"


class Config(BaseModel):
    """Main configuration for ollama-ctl."""

    default_host: str = "local"
    hosts: dict[str, HostConfig] = Field(
        default_factory=lambda: {"local": HostConfig(hostname="localhost")}
    )
    settings: dict[str, Any] = Field(default_factory=dict)

    def get_host_config(self, host_alias: Optional[str] = None) -> HostConfig:
        """Get host config by alias, or return default host config."""
        if host_alias is None:
            host_alias = self.default_host

        if host_alias in self.hosts:
            return self.hosts[host_alias]

        # If not found in config, treat as direct hostname/IP
        # Parse potential port from hostname:port format
        if ":" in host_alias:
            hostname, port_str = host_alias.rsplit(":", 1)
            try:
                port = int(port_str)
                return HostConfig(hostname=hostname, port=port)
            except ValueError:
                # Not a valid port, treat entire string as hostname
                pass

        return HostConfig(hostname=host_alias)


class ModelDetails(BaseModel):
    """Details about a model."""

    parent_model: Optional[str] = None
    format: Optional[str] = None
    family: Optional[str] = None
    families: Optional[list[str]] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None


class ModelInfo(BaseModel):
    """Information about an Ollama model."""

    name: str
    model: str = ""  # Some API responses use 'model' instead of 'name'
    modified_at: str
    size: int
    digest: str
    details: Optional[ModelDetails] = None

    def get_name(self) -> str:
        """Get the model name (handles both 'name' and 'model' fields)."""
        return self.name or self.model


class GenerateRequest(BaseModel):
    """Request for generating text."""

    model: str
    prompt: str
    stream: bool = True
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[list[int]] = None
    options: Optional[dict[str, Any]] = None
    format: Optional[str] = None
    raw: bool = False
    keep_alive: Optional[str] = None


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""

    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[list[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class ChatMessage(BaseModel):
    """A message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str
    images: Optional[list[str]] = None


class ChatRequest(BaseModel):
    """Request for chat endpoint."""

    model: str
    messages: list[ChatMessage]
    stream: bool = True
    format: Optional[str] = None
    options: Optional[dict[str, Any]] = None
    template: Optional[str] = None
    keep_alive: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    model: str
    created_at: str
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class PullRequest(BaseModel):
    """Request to pull a model."""

    name: str
    insecure: bool = False
    stream: bool = True


class PullResponse(BaseModel):
    """Response from pull endpoint (streaming)."""

    status: str
    digest: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None


class PushRequest(BaseModel):
    """Request to push a model."""

    name: str
    insecure: bool = False
    stream: bool = True


class PushResponse(BaseModel):
    """Response from push endpoint (streaming)."""

    status: str
    digest: Optional[str] = None
    total: Optional[int] = None
    completed: Optional[int] = None


class DeleteRequest(BaseModel):
    """Request to delete a model."""

    name: str


class ShowRequest(BaseModel):
    """Request to show model information."""

    name: str


class ShowResponse(BaseModel):
    """Response from show endpoint."""

    modelfile: Optional[str] = None
    parameters: Optional[str] = None
    template: Optional[str] = None
    details: Optional[ModelDetails] = None
    model_info: Optional[dict[str, Any]] = None


class ListModelsResponse(BaseModel):
    """Response from list models endpoint."""

    models: list[ModelInfo]


class EmbeddingsRequest(BaseModel):
    """Request for embeddings."""

    model: str
    prompt: str
    options: Optional[dict[str, Any]] = None
    keep_alive: Optional[str] = None


class EmbeddingsResponse(BaseModel):
    """Response from embeddings endpoint."""

    embedding: list[float]
