# MunchFORsen - LLM Proxy Server

[![Build Executables](https://github.com/FOR-sight-ai/munchFORsen/actions/workflows/build-executables.yml/badge.svg)](https://github.com/FOR-sight-ai/munchFORsen/actions/workflows/build-executables.yml)
[![Latest Release](https://img.shields.io/github/v/release/FOR-sight-ai/munchFORsen)](https://github.com/FOR-sight-ai/munchFORsen/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/FOR-sight-ai/munchFORsen/total)](https://github.com/FOR-sight-ai/munchFORsen/releases)

A simple FastAPI proxy server for calling LLMs with HTTP request logging and replay capabilities.

## Features

- HTTP proxy with FastAPI
- Optional request logging (disabled by default)
- Request replay from logs
- Support for header and target URL modification
- Header merging from JSON files (for API keys and authentication)
- Content flattening for single-text message arrays
- Tool role replacement for compatibility with different LLM providers

## Installation

### Development

```bash
# Clone the repository
git clone https://github.com/FOR-sight-ai/munchFORsen.git
cd munchFORsen

# Install dependencies with UV
uv sync

# Start the server (development mode with auto-reload)
uv run uvicorn proxy:app --reload

# Or run the server directly with command-line options
uv run python proxy.py server --port 8000
```

## Local Build

### Prerequisites

- Python 3.12+
- UV (package manager)

### Build the executable

**On macOS/Linux:**
```bash
./build.sh
```

**On Windows:**
```cmd
build.bat
```

Or manually:
```bash
uv add pyinstaller
uv run pyinstaller proxy.spec
```

The executable will be created in the `dist/` folder.

## Usage

### Start the server

```bash
# Basic usage
python proxy.py server

# With custom options
python proxy.py server --port 9000 --host 127.0.0.1

# Enable content flattening (converts single-text content arrays to strings)
python proxy.py server --flatten-content

# Replace tool-call and tool-response roles with user role
python proxy.py server --no-tool-roles

# Enable request logging (disabled by default)
python proxy.py server --log

# Merge headers from JSON file (for API keys and authentication)
python proxy.py server --merge-header headers.json

# With the executable
./dist/proxy server --host 0.0.0.0 --port 8000
```

### Content Flattening

The `--flatten-content` option automatically converts message content from array format to string format when the array contains only a single text element. This is useful for APIs that expect simplified content structures.

**Example transformation:**
```json
// Before flattening
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Hello, world!"
        }
      ]
    }
  ]
}

// After flattening
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, world!"
    }
  ]
}
```

**Note:** Only single-element arrays with `type: "text"` are flattened. Multi-element arrays and other content types remain unchanged.

### Request Logging

By default, request logging is disabled to improve performance and reduce disk usage. Use the `--log` flag to enable logging of all requests to files. These logs can later be used with the replay functionality.

```bash
# Enable request logging
python proxy.py server --log
```

Logs are saved in:
- Windows: `%USERPROFILE%\AppData\Local\Proxy\logs`
- macOS/Linux: `~/.local/share/proxy/logs`

### Tool Role Replacement

The `--no-tool-roles` option replaces "tool-call" and "tool-response" roles with "user" role in messages. This is useful for compatibility with LLM providers that don't support these specialized roles.

**Example transformation:**
```json
// Before replacement
{
  "messages": [
    {
      "role": "user",
      "content": "What's the weather?"
    },
    {
      "role": "tool-call",
      "content": "Calling weather API..."
    },
    {
      "role": "tool-response",
      "content": "It's sunny, 75°F"
    }
  ]
}

// After replacement
{
  "messages": [
    {
      "role": "user",
      "content": "What's the weather?"
    },
    {
      "role": "user",
      "content": "Calling weather API..."
    },
    {
      "role": "user",
      "content": "It's sunny, 75°F"
    }
  ]
}
```

### Header Merging

The `--merge-header` option allows you to load headers from a JSON file and merge them with each request. This is particularly useful for adding API keys and authentication headers without hardcoding them in your application.

**Usage:**
```bash
# Start server with header merging
python proxy.py server --merge-header headers.json

# Replay with header merging
python proxy.py replay log_file.json --merge-header headers.json
```

**Behavior:**
- Headers from the JSON file are merged with incoming request headers
- If a header already exists in the request, it will be replaced by the one from the file (case-insensitive matching)
- The header names from the JSON file are preserved exactly as written
- All header keys and values must be strings

**Security Note:** Keep your header files secure as they may contain sensitive API keys and tokens. Consider using environment variables or secure storage for production deployments.

### Replay Requests

```bash
# Replay a saved request
python proxy.py replay <log_file_path>

# Replay with content flattening
python proxy.py replay <log_file_path> --flatten-content

# Replay with header merging
python proxy.py replay <log_file_path> --merge-header headers.json

# Replay to a different endpoint
python proxy.py replay <log_file_path> --target-url https://api.openai.com/v1/chat/completions
```

## Running in Linux or Docker Environments

### Linux Environment

You can run the server directly using `uv run` without installing the package:

```bash
# Clone the repository
git clone https://github.com/FOR-sight-ai/munchFORsen.git
cd munchFORsen

# Install dependencies with UV
uv sync

# Run the server with options
uv run python proxy.py server --host 0.0.0.0 --port 8000 --log
```

### Docker Environment

You can run the server in a Docker container:

```bash
# Clone the repository
git clone https://github.com/FOR-sight-ai/munchFORsen.git
cd munchFORsen

# Build the Docker image
docker build -t munchforsen .

# Run the container
docker run -p 8000:8000 munchforsen

# Or with custom options
docker run -p 9000:9000 munchforsen python proxy.py server --host 0.0.0.0 --port 9000 --log --flatten-content
```

## Acknowledgement
This project received funding from the French ”IA Cluster” program within the Artificial and Natural Intelligence Toulouse Institute (ANITI) and from the "France 2030" program within IRT Saint Exupery. The authors gratefully acknowledge the support of the FOR projects.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
