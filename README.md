# MunchFORsen - LLM Proxy Server

[![Build Executables](https://github.com/FOR-sight-ai/munchFORsen/actions/workflows/build-executables.yml/badge.svg)](https://github.com/FOR-sight-ai/munchFORsen/actions/workflows/build-executables.yml)
[![Latest Release](https://img.shields.io/github/v/release/FOR-sight-ai/munchFORsen)](https://github.com/FOR-sight-ai/munchFORsen/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/FOR-sight-ai/munchFORsen/total)](https://github.com/FOR-sight-ai/munchFORsen/releases)

A simple FastAPI proxy server for calling LLMs with HTTP request logging and replay capabilities.

## Features

- HTTP proxy with FastAPI
- Automatic request logging
- Request replay from logs
- Support for header and target URL modification
- Content flattening for single-text message arrays

## Installation

### Development

```bash
# Clone the repository
git clone https://github.com/FOR-sight-ai/munchFORsen.git
cd munchFORsen

# Install dependencies with UV
uv sync

# Start the server
uv run uvicorn proxy:app --reload
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

### Replay Requests

```bash
# Replay a saved request
python proxy.py replay <log_file_path>

# Replay with content flattening
python proxy.py replay <log_file_path> --flatten-content

# Replay to a different endpoint
python proxy.py replay <log_file_path> --target-url https://api.openai.com/v1/chat/completions
```


## Acknowledgement
This project received funding from the French ”IA Cluster” program within the Artificial and Natural Intelligence Toulouse Institute (ANITI) and from the "France 2030" program within IRT Saint Exupery. The authors gratefully acknowledge the support of the FOR projects.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
