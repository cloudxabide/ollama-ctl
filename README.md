# ollama-ctl

A powerful CLI utility for managing multiple Ollama servers with support for Model Context Protocol (MCP) integration.

NOTE: I *just* started working on this with Claude.  I am NOT a developer/programmer (I am an "infra guy", mostly).  Therefore, do not expect much from this code - do not implicitly trust it (ie. review the code).  I am building with Claude and testing somewhat frequently - I do not anticipate any significant issues, but.. my advice still applies.  Have fun - Claude and I are.

## Features

- **Multi-server Management**: Configure and manage multiple Ollama servers with simple aliases
- **Full API Coverage**: Access all Ollama operations - list, pull, push, delete, run, and chat
- **MCP Integration**: Seamlessly integrate with Model Context Protocol configurations
- **Beautiful Output**: Rich terminal interface with tables, progress bars, and streaming
- **Flexible Configuration**: YAML-based config with environment variable support
- **Easy Installation**: Available via pip or Homebrew

## Installation

### Via pip

```bash
pip install ollama-ctl
```

### Via Homebrew

```bash
brew tap cloudxabide/ollama-ctl
brew install ollama-ctl
```

### From source

```bash
git clone https://github.com/cloudxabide/ollama-ctl.git
cd ollama-ctl
pip install -e .
```

## Quick Start

### Initialize Configuration

Create a default configuration file:

```bash
ollama-ctl init-config
```

This creates a config at `~/.config/ollama-ctl/config.yaml` (or platform equivalent).

### Basic Usage

```bash
# List available models on default server
ollama-ctl list-models

# List models on specific server
ollama-ctl list-models -h remote

# Run a prompt
ollama-ctl run -m llama2 "What is Python?"

# Run on specific server
ollama-ctl run -h remote -m llama2 "Hello world"

# Interactive chat
ollama-ctl chat -m llama2

# Pull a model
ollama-ctl pull llama2

# Check server health
ollama-ctl health -h remote
```

## Configuration

### Configuration File Format

The configuration file uses YAML format:

```yaml
# Default host to use when none is specified
default_host: local

# Host configurations
hosts:
  local:
    hostname: localhost
    port: 11434
    protocol: http
    verify_ssl: true

  remote:
    hostname: 192.168.1.100
    port: 11434
    protocol: https
    verify_ssl: true

  cloud:
    hostname: ollama.example.com
    port: 443
    protocol: https
    verify_ssl: true

# Global settings
settings:
  timeout: 30
  stream: true
  default_model: llama2
```

### Configuration Locations

Configuration files are loaded in this priority order:

1. Specified via `--config` flag
2. Local project config: `./.ollama-ctl.yaml`
3. Global config: `~/.config/ollama-ctl/config.yaml` (Linux/macOS)
4. Environment variables: `OLLAMA_HOST`, `OLLAMA_PORT`, `OLLAMA_PROTOCOL`

### Environment Variables

You can override configuration using environment variables:

```bash
export OLLAMA_HOST=192.168.1.100
export OLLAMA_PORT=11434
export OLLAMA_PROTOCOL=https

ollama-ctl list-models
```

## Commands

### `list-models`

List all available models on a server.

```bash
ollama-ctl list-models [OPTIONS]

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  --json             Output as JSON
```

### `run`

Run a prompt against a model.

```bash
ollama-ctl run [OPTIONS] PROMPT

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  -m, --model TEXT   Model name [required]
  --system TEXT      System message
  --no-stream        Disable streaming output
```

### `chat`

Interactive chat with a model.

```bash
ollama-ctl chat [OPTIONS]

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  -m, --model TEXT   Model name [required]
  --system TEXT      System message
```

### `pull`

Pull a model from the registry.

```bash
ollama-ctl pull [OPTIONS] MODEL

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  --insecure         Allow insecure connections
```

### `push`

Push a model to the registry.

```bash
ollama-ctl push [OPTIONS] MODEL

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  --insecure         Allow insecure connections
```

### `delete`

Delete a model from the server.

```bash
ollama-ctl delete [OPTIONS] MODEL

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
  -y, --yes          Skip confirmation
```

### `show`

Show details about a model.

```bash
ollama-ctl show [OPTIONS] MODEL

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
```

### `health`

Check if an Ollama server is reachable.

```bash
ollama-ctl health [OPTIONS]

Options:
  -h, --host TEXT    Host alias or hostname
  -p, --port INTEGER Port number
```

### `init-config`

Create an example configuration file.

```bash
ollama-ctl init-config [OPTIONS]

Options:
  -o, --output PATH  Output path
```

## MCP Integration

ollama-ctl supports Model Context Protocol (MCP) configurations, allowing seamless integration with tools like Cursor and Claude Desktop.

### Using MCP Configuration

```bash
# Use MCP config for host resolution
ollama-ctl --mcphost-config list-models

# Run with MCP hosts
ollama-ctl --mcphost-config run -m llama2 "Hello"
```

### MCP Configuration Locations

ollama-ctl searches for MCP configs in:

1. `.cursor/mcp.json` (project-specific, Cursor editor)
2. `~/.cursor/mcp.json` (global Cursor config)
3. `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
4. `~/.config/Claude/claude_desktop_config.json` (Linux)

### MCP Configuration Format

Example MCP configuration:

```json
{
  "mcpServers": {
    "ollama-local": {
      "command": "ollama",
      "args": ["serve"],
      "env": {
        "OLLAMA_HOST": "localhost:11434"
      }
    },
    "ollama-remote": {
      "command": "ssh",
      "args": ["user@remote", "ollama", "serve"],
      "env": {
        "OLLAMA_HOST": "https://192.168.1.100:11434"
      }
    }
  }
}
```

ollama-ctl automatically detects Ollama servers in your MCP config and makes them available as host aliases.

## Advanced Usage

### Direct Hostname Usage

You can use hostnames directly without configuring them:

```bash
# Use direct hostname
ollama-ctl list-models -h 192.168.1.100

# With custom port
ollama-ctl list-models -h 192.168.1.100 -p 8080

# Hostname:port format
ollama-ctl list-models -h myserver.local:11434
```

### System Messages

Add system context to your prompts:

```bash
ollama-ctl run -m llama2 \
  --system "You are a helpful Python expert" \
  "How do I use list comprehensions?"
```

### JSON Output

Get machine-readable output:

```bash
ollama-ctl list-models --json | jq '.[] | .name'
```

### Batch Operations

Process multiple prompts:

```bash
# Using a loop
for prompt in "Hello" "Goodbye" "How are you?"; do
  ollama-ctl run -m llama2 "$prompt"
done
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/cloudxabide/ollama-ctl.git
cd ollama-ctl

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ollama_ctl --cov-report=html

# Run specific test file
pytest tests/test_config.py
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## Architecture

ollama-ctl is built with:

- **Click**: CLI framework for command-line interface
- **httpx**: Modern HTTP client for API requests
- **Pydantic**: Data validation and settings management
- **Rich**: Beautiful terminal output
- **PyYAML**: YAML configuration parsing
- **platformdirs**: Cross-platform config directory paths

### Project Structure

```
ollama-ctl/
├── src/ollama_ctl/
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # CLI commands (Click)
│   ├── client.py         # Ollama API client
│   ├── config.py         # Configuration management
│   ├── mcp.py            # MCP integration
│   ├── models.py         # Pydantic data models
│   └── utils.py          # Helper functions
├── tests/                # Test suite
├── examples/             # Example configs
└── pyproject.toml        # Project configuration
```

## Troubleshooting

### Connection Errors

If you get connection errors:

1. Check if Ollama is running: `ollama serve`
2. Verify the host and port are correct
3. Use `ollama-ctl health -h <host>` to test connectivity
4. Check firewall settings for remote servers

### Model Not Found

If a model isn't found:

1. List available models: `ollama-ctl list-models`
2. Pull the model: `ollama-ctl pull <model-name>`
3. Verify you're connected to the right server

### Configuration Issues

If configuration isn't loading:

1. Check config file location: `~/.config/ollama-ctl/config.yaml`
2. Validate YAML syntax
3. Use `ollama-ctl init-config` to create a new config
4. Check environment variables: `echo $OLLAMA_HOST`

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run tests and linters
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built for the [Ollama](https://ollama.ai/) project
- Inspired by the Model Context Protocol
- Uses [Click](https://click.palletsprojects.com/) for CLI
- Beautiful output powered by [Rich](https://rich.readthedocs.io/)

## Links

- **Repository**: https://github.com/cloudxabide/ollama-ctl
- **Issues**: https://github.com/cloudxabide/ollama-ctl/issues
- **Ollama**: https://ollama.ai/
- **MCP**: https://modelcontextprotocol.io/
