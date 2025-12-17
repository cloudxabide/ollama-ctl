"""Ollama REST API client."""

import json
from typing import Any, Generator, Optional, Union

import httpx
from pydantic import ValidationError

from ollama_ctl.models import (
    ChatRequest,
    ChatResponse,
    DeleteRequest,
    EmbeddingsRequest,
    EmbeddingsResponse,
    GenerateRequest,
    GenerateResponse,
    HostConfig,
    ListModelsResponse,
    ModelInfo,
    PullRequest,
    PullResponse,
    PushRequest,
    PushResponse,
    ShowRequest,
    ShowResponse,
)


class OllamaClientError(Exception):
    """Base exception for Ollama client errors."""

    pass


class OllamaConnectionError(OllamaClientError):
    """Raised when connection to Ollama server fails."""

    pass


class OllamaAPIError(OllamaClientError):
    """Raised when Ollama API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OllamaClient:
    """Client for interacting with Ollama REST API."""

    def __init__(
        self,
        host_config: HostConfig,
        timeout: int = 120,
    ):
        """Initialize the Ollama client.

        Args:
            host_config: Configuration for the Ollama host
            timeout: Request timeout in seconds (default: 120)
        """
        self.host_config = host_config
        self.base_url = host_config.get_base_url()
        self.timeout = timeout

        # Create httpx client with appropriate settings
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            verify=host_config.verify_ssl,
            follow_redirects=True,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make an HTTP request to the Ollama API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            json_data: Optional JSON data to send

        Returns:
            Response data as dictionary

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        try:
            response = self.client.request(method, endpoint, json=json_data)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama server at {self.base_url}: {e}"
            )
        except httpx.TimeoutException as e:
            raise OllamaConnectionError(f"Request to {self.base_url} timed out: {e}")
        except httpx.HTTPStatusError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise OllamaAPIError(error_msg, e.response.status_code)
        except Exception as e:
            raise OllamaClientError(f"Unexpected error: {e}")

    def _stream_request(
        self, method: str, endpoint: str, json_data: dict
    ) -> Generator[dict[str, Any], None, None]:
        """Make a streaming HTTP request to the Ollama API.

        Args:
            method: HTTP method (POST)
            endpoint: API endpoint path
            json_data: JSON data to send

        Yields:
            Response chunks as dictionaries

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        try:
            with self.client.stream(method, endpoint, json=json_data) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama server at {self.base_url}: {e}"
            )
        except httpx.TimeoutException as e:
            raise OllamaConnectionError(f"Request to {self.base_url} timed out: {e}")
        except httpx.HTTPStatusError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise OllamaAPIError(error_msg, e.response.status_code)

    # Model Management

    def list_models(self) -> list[ModelInfo]:
        """List all available models.

        Returns:
            List of ModelInfo objects

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        data = self._make_request("GET", "/api/tags")
        try:
            response = ListModelsResponse(**data)
            return response.models
        except ValidationError as e:
            raise OllamaClientError(f"Failed to parse models list: {e}")

    def show_model(self, name: str) -> ShowResponse:
        """Show details about a specific model.

        Args:
            name: Model name

        Returns:
            ShowResponse with model details

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = ShowRequest(name=name)
        data = self._make_request("POST", "/api/show", request.model_dump())
        try:
            return ShowResponse(**data)
        except ValidationError as e:
            raise OllamaClientError(f"Failed to parse model details: {e}")

    def pull_model(
        self, name: str, stream: bool = True, insecure: bool = False
    ) -> Union[Generator[PullResponse, None, None], dict[str, Any]]:
        """Pull a model from the registry.

        Args:
            name: Model name to pull
            stream: Whether to stream progress updates
            insecure: Allow insecure connections

        Yields:
            PullResponse objects with progress updates (if streaming)

        Returns:
            Final response dictionary (if not streaming)

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = PullRequest(name=name, stream=stream, insecure=insecure)

        if stream:

            def generator():
                for chunk in self._stream_request("POST", "/api/pull", request.model_dump()):
                    try:
                        yield PullResponse(**chunk)
                    except ValidationError:
                        # Skip invalid chunks
                        continue

            return generator()
        else:
            return self._make_request("POST", "/api/pull", request.model_dump())

    def push_model(
        self, name: str, stream: bool = True, insecure: bool = False
    ) -> Union[Generator[PushResponse, None, None], dict[str, Any]]:
        """Push a model to the registry.

        Args:
            name: Model name to push
            stream: Whether to stream progress updates
            insecure: Allow insecure connections

        Yields:
            PushResponse objects with progress updates (if streaming)

        Returns:
            Final response dictionary (if not streaming)

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = PushRequest(name=name, stream=stream, insecure=insecure)

        if stream:

            def generator():
                for chunk in self._stream_request("POST", "/api/push", request.model_dump()):
                    try:
                        yield PushResponse(**chunk)
                    except ValidationError:
                        # Skip invalid chunks
                        continue

            return generator()
        else:
            return self._make_request("POST", "/api/push", request.model_dump())

    def delete_model(self, name: str) -> None:
        """Delete a model.

        Args:
            name: Model name to delete

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = DeleteRequest(name=name)
        self._make_request("DELETE", "/api/delete", request.model_dump())

    # Generation

    def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = True,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[list[int]] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> Union[Generator[GenerateResponse, None, None], GenerateResponse]:
        """Generate text from a prompt.

        Args:
            model: Model name to use
            prompt: Prompt text
            stream: Whether to stream responses
            system: System message
            template: Prompt template
            context: Context from previous response
            options: Additional model options

        Yields:
            GenerateResponse objects (if streaming)

        Returns:
            Final GenerateResponse (if not streaming)

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = GenerateRequest(
            model=model,
            prompt=prompt,
            stream=stream,
            system=system,
            template=template,
            context=context,
            options=options,
        )

        if stream:

            def generator():
                for chunk in self._stream_request("POST", "/api/generate", request.model_dump()):
                    try:
                        yield GenerateResponse(**chunk)
                    except ValidationError:
                        # Skip invalid chunks
                        continue

            return generator()
        else:
            data = self._make_request("POST", "/api/generate", request.model_dump())
            try:
                return GenerateResponse(**data)
            except ValidationError as e:
                raise OllamaClientError(f"Failed to parse generate response: {e}")

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        stream: bool = True,
        options: Optional[dict[str, Any]] = None,
    ) -> Union[Generator[ChatResponse, None, None], ChatResponse]:
        """Have a chat conversation.

        Args:
            model: Model name to use
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream responses
            options: Additional model options

        Yields:
            ChatResponse objects (if streaming)

        Returns:
            Final ChatResponse (if not streaming)

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = ChatRequest(
            model=model,
            messages=messages,  # type: ignore
            stream=stream,
            options=options,
        )

        if stream:

            def generator():
                for chunk in self._stream_request("POST", "/api/chat", request.model_dump()):
                    try:
                        yield ChatResponse(**chunk)
                    except ValidationError:
                        # Skip invalid chunks
                        continue

            return generator()
        else:
            data = self._make_request("POST", "/api/chat", request.model_dump())
            try:
                return ChatResponse(**data)
            except ValidationError as e:
                raise OllamaClientError(f"Failed to parse chat response: {e}")

    # Utilities

    def embeddings(
        self, model: str, prompt: str, options: Optional[dict[str, Any]] = None
    ) -> list[float]:
        """Generate embeddings for text.

        Args:
            model: Model name to use
            prompt: Text to generate embeddings for
            options: Additional model options

        Returns:
            List of embedding values

        Raises:
            OllamaConnectionError: If connection fails
            OllamaAPIError: If API returns an error
        """
        request = EmbeddingsRequest(model=model, prompt=prompt, options=options)
        data = self._make_request("POST", "/api/embeddings", request.model_dump())
        try:
            response = EmbeddingsResponse(**data)
            return response.embedding
        except ValidationError as e:
            raise OllamaClientError(f"Failed to parse embeddings response: {e}")

    def health_check(self) -> bool:
        """Check if the Ollama server is reachable.

        Returns:
            True if server is reachable, False otherwise
        """
        try:
            self._make_request("GET", "/")
            return True
        except Exception:
            return False
