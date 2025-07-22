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
- Automatic token request for OAuth2 and similar authentication flows
- Content flattening for single-text message arrays
- Tool role replacement for compatibility with different LLM providers
- Corporate proxy support with optional authentication

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

# Enable automatic token request for OAuth2 authentication
python proxy.py server --token-request token_config.json

# Use corporate proxy for all requests
python proxy.py server --proxy-url http://proxy.company.com:8080

# Use corporate proxy with authentication
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password

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

### Token Request (OAuth2 Authentication)

The `--token-request` option enables automatic token acquisition for APIs that require OAuth2 or similar token-based authentication. Before each proxied request, the server will automatically obtain a fresh token and add it to the `Authorization` header as `Bearer {token}`.

**Usage:**
```bash
# Start server with token request enabled
python proxy.py server --token-request token_config.json

# Replay with token request enabled
python proxy.py replay log_file.json --token-request token_config.json
```

**Configuration File Format:**
Create a JSON file with your token request parameters:

```json
{
  "url": "https://auth.example.com/oauth/token",
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded"
  },
  "data": {
    "grant_type": "client_credentials",
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",
    "scope": "api:read api:write"
  },
  "token_field": "access_token"
}
```

**Configuration Fields:**
- `url` (required): Token endpoint URL
- `method` (optional): HTTP method, defaults to "POST"
- `headers` (optional): Headers for the token request
- `data` (optional): Request data (form data for POST requests)
- `token_field` (optional): Response field containing the token, defaults to "access_token"

**Example curl equivalent:**
```bash
curl -X POST \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     -d "client_id=your_client_id_here" \
     -d "client_secret=your_client_secret_here" \
     -d "scope=api:read api:write" \
     "https://auth.example.com/oauth/token"
```

**Behavior:**
- A fresh token is requested before each proxied request
- The obtained token replaces any existing `Authorization` header
- If token request fails, the proxy returns a 500 error with details

**Security Note:** Keep your token configuration files secure as they contain sensitive credentials. Consider using environment variables for production deployments.

### Corporate Proxy Support

The `--proxy-url` and `--proxy-auth` options enable the proxy server to work through corporate firewalls and proxy servers. All HTTP requests (including token requests and API calls) will be routed through the specified proxy.

**Usage:**
```bash
# Basic proxy usage (no authentication)
python proxy.py server --proxy-url http://proxy.company.com:8080

# Proxy with authentication
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password

# HTTPS proxy
python proxy.py server --proxy-url https://secure-proxy.company.com:8080 --proxy-auth username:password

# Replay with proxy
python proxy.py replay log_file.json --proxy-url http://proxy.company.com:8080 --proxy-auth username:password
```

**Supported Proxy Types:**
- HTTP proxies (`http://proxy.example.com:8080`)
- HTTPS proxies (`https://proxy.example.com:8080`)
- Authenticated proxies (using `--proxy-auth username:password`)

**Behavior:**
- All outbound HTTP requests (API calls, token requests) are routed through the proxy
- Proxy authentication is handled automatically when configured
- Both server and replay modes support proxy configuration
- Proxy settings are applied globally to all HTTP clients

**Security Note:** Proxy credentials are passed as command-line arguments. In production environments, consider using environment variables or configuration files to avoid exposing credentials in process lists.

### Replay Requests

```bash
# Replay a saved request
python proxy.py replay <log_file_path>

# Replay with content flattening
python proxy.py replay <log_file_path> --flatten-content

# Replay with header merging
python proxy.py replay <log_file_path> --merge-header headers.json

# Replay with token request
python proxy.py replay <log_file_path> --token-request token_config.json

# Replay with corporate proxy
python proxy.py replay <log_file_path> --proxy-url http://proxy.company.com:8080 --proxy-auth username:password

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

# With corporate proxy
docker run -p 8000:8000 munchforsen python proxy.py server --host 0.0.0.0 --port 8000 --proxy-url http://proxy.company.com:8080 --proxy-auth username:password
```

## Acknowledgement
This project received funding from the French ”IA Cluster” program within the Artificial and Natural Intelligence Toulouse Institute (ANITI) and from the "France 2030" program within IRT Saint Exupery. The authors gratefully acknowledge the support of the FOR projects.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
