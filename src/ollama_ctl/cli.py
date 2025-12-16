"""Command-line interface for ollama-ctl."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ollama_ctl.client import (
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaAPIError,
)
from ollama_ctl.config import load_config, get_default_config_path, create_example_config
from ollama_ctl.models import Config, ChatMessage

console = Console()


def get_client_from_context(
    ctx: click.Context, host: Optional[str] = None, port: Optional[int] = None
) -> OllamaClient:
    """Get an OllamaClient from the Click context.

    Args:
        ctx: Click context
        host: Optional host override
        port: Optional port override

    Returns:
        Configured OllamaClient
    """
    config: Config = ctx.obj["config"]

    # Get host config
    if host:
        host_config = config.get_host_config(host)
    else:
        host_config = config.get_host_config()

    # Override port if specified
    if port:
        host_config.port = port

    timeout = config.settings.get("timeout", 120)
    return OllamaClient(host_config, timeout=timeout)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--mcphost-config",
    is_flag=True,
    help="Use MCP configuration for hosts",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], mcphost_config: bool):
    """ollama-ctl: CLI utility for managing Ollama servers.

    Manage multiple Ollama servers, run models, and integrate with MCP.
    """
    ctx.ensure_object(dict)

    try:
        # Load configuration
        cfg = load_config(config)

        # If MCP flag is set, merge MCP config
        if mcphost_config:
            from ollama_ctl.mcp import load_mcp_config, merge_mcp_hosts

            mcp_cfg = load_mcp_config()
            if mcp_cfg:
                mcp_hosts = mcp_cfg.extract_ollama_hosts()
                cfg = merge_mcp_hosts(cfg, mcp_hosts)

        ctx.obj["config"] = cfg
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@cli.command("list-models")
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_models(
    ctx: click.Context, host: Optional[str], port: Optional[int], output_json: bool
):
    """List all available models on the Ollama server."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            models = client.list_models()

            if output_json:
                import json

                model_data = [
                    {
                        "name": m.get_name(),
                        "size": m.size,
                        "modified_at": m.modified_at,
                        "digest": m.digest,
                    }
                    for m in models
                ]
                click.echo(json.dumps(model_data, indent=2))
            else:
                if not models:
                    console.print("[yellow]No models found[/yellow]")
                    return

                table = Table(title="Available Models")
                table.add_column("Name", style="cyan")
                table.add_column("Size", style="green")
                table.add_column("Modified", style="blue")

                for model in models:
                    # Format size in human-readable format
                    size_gb = model.size / (1024**3)
                    size_str = f"{size_gb:.2f} GB"

                    table.add_row(model.get_name(), size_str, model.modified_at)

                console.print(table)
    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.option("--model", "-m", required=True, help="Model name")
@click.argument("prompt")
@click.option("--system", help="System message")
@click.option("--no-stream", is_flag=True, help="Disable streaming output")
@click.pass_context
def run(
    ctx: click.Context,
    host: Optional[str],
    port: Optional[int],
    model: str,
    prompt: str,
    system: Optional[str],
    no_stream: bool,
):
    """Run a prompt against a model."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            stream = not no_stream

            if stream:
                # Streaming output
                response_text = ""
                for chunk in client.generate(model, prompt, stream=True, system=system):
                    response_text += chunk.response
                    click.echo(chunk.response, nl=False)

                click.echo()  # Final newline
            else:
                # Non-streaming output
                response = client.generate(model, prompt, stream=False, system=system)
                click.echo(response.response)

    except OllamaConnectionError as e:
        console.print(f"\n[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"\n[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.argument("model")
@click.option("--insecure", is_flag=True, help="Allow insecure connections")
@click.pass_context
def pull(
    ctx: click.Context, host: Optional[str], port: Optional[int], model: str, insecure: bool
):
    """Pull a model from the registry."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            console.print(f"[cyan]Pulling model: {model}[/cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading...", total=None)

                for chunk in client.pull_model(model, stream=True, insecure=insecure):
                    progress.update(task, description=chunk.status)

                    if chunk.done:
                        progress.update(task, description="[green]Complete![/green]")

            console.print(f"[green]Successfully pulled {model}[/green]")
    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.argument("model")
@click.option("--insecure", is_flag=True, help="Allow insecure connections")
@click.pass_context
def push(
    ctx: click.Context, host: Optional[str], port: Optional[int], model: str, insecure: bool
):
    """Push a model to the registry."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            console.print(f"[cyan]Pushing model: {model}[/cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Uploading...", total=None)

                for chunk in client.push_model(model, stream=True, insecure=insecure):
                    progress.update(task, description=chunk.status)

                    if chunk.done:
                        progress.update(task, description="[green]Complete![/green]")

            console.print(f"[green]Successfully pushed {model}[/green]")
    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.argument("model")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(
    ctx: click.Context, host: Optional[str], port: Optional[int], model: str, yes: bool
):
    """Delete a model from the server."""
    try:
        if not yes:
            if not click.confirm(f"Are you sure you want to delete model '{model}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        with get_client_from_context(ctx, host, port) as client:
            client.delete_model(model)
            console.print(f"[green]Successfully deleted {model}[/green]")
    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.argument("model")
@click.pass_context
def show(ctx: click.Context, host: Optional[str], port: Optional[int], model: str):
    """Show details about a model."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            info = client.show_model(model)

            console.print(f"\n[bold cyan]Model: {model}[/bold cyan]\n")

            if info.details:
                console.print("[bold]Details:[/bold]")
                if info.details.family:
                    console.print(f"  Family: {info.details.family}")
                if info.details.parameter_size:
                    console.print(f"  Parameters: {info.details.parameter_size}")
                if info.details.quantization_level:
                    console.print(f"  Quantization: {info.details.quantization_level}")

            if info.modelfile:
                console.print("\n[bold]Modelfile:[/bold]")
                console.print(info.modelfile)

            if info.parameters:
                console.print("\n[bold]Parameters:[/bold]")
                console.print(info.parameters)

    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.option("--model", "-m", required=True, help="Model name")
@click.option("--system", help="System message")
@click.pass_context
def chat(
    ctx: click.Context,
    host: Optional[str],
    port: Optional[int],
    model: str,
    system: Optional[str],
):
    """Interactive chat with a model.

    Type your messages and press Enter. Type 'exit' or 'quit' to end the chat.
    """
    try:
        with get_client_from_context(ctx, host, port) as client:
            messages = []

            if system:
                messages.append({"role": "system", "content": system})

            console.print(
                f"\n[bold cyan]Chat with {model}[/bold cyan] (type 'exit' or 'quit' to end)\n"
            )

            while True:
                try:
                    user_input = click.prompt("You", type=str)

                    if user_input.lower() in ("exit", "quit"):
                        console.print("[yellow]Goodbye![/yellow]")
                        break

                    messages.append({"role": "user", "content": user_input})

                    # Stream the response
                    console.print("[cyan]Assistant:[/cyan] ", end="")
                    response_text = ""

                    for chunk in client.chat(model, messages, stream=True):
                        if chunk.message:
                            content = chunk.message.content
                            response_text += content
                            click.echo(content, nl=False)

                    click.echo()  # Newline after response

                    # Add assistant response to history
                    messages.append({"role": "assistant", "content": response_text})

                except KeyboardInterrupt:
                    console.print("\n[yellow]Chat ended[/yellow]")
                    break

    except OllamaConnectionError as e:
        console.print(f"[red]Connection error: {e}[/red]")
        sys.exit(1)
    except OllamaAPIError as e:
        console.print(f"[red]API error: {e}[/red]")
        sys.exit(1)
    except OllamaClientError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command("init-config")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path (default: ~/.config/ollama-ctl/config.yaml)",
)
def init_config(output: Optional[Path]):
    """Create an example configuration file."""
    try:
        if output is None:
            output = get_default_config_path()

        if output.exists():
            if not click.confirm(f"Config file already exists at {output}. Overwrite?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        create_example_config(output)
        console.print(f"[green]Created example config at {output}[/green]")
        console.print("\nEdit this file to add your Ollama servers.")
    except Exception as e:
        console.print(f"[red]Error creating config: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", "-h", help="Host alias or hostname")
@click.option("--port", "-p", type=int, help="Port number (default: 11434)")
@click.pass_context
def health(ctx: click.Context, host: Optional[str], port: Optional[int]):
    """Check if an Ollama server is reachable."""
    try:
        with get_client_from_context(ctx, host, port) as client:
            if client.health_check():
                console.print(
                    f"[green]✓ Server at {client.base_url} is reachable[/green]"
                )
            else:
                console.print(f"[red]✗ Server at {client.base_url} is not reachable[/red]")
                sys.exit(1)
    except OllamaConnectionError as e:
        console.print(f"[red]✗ Connection error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
