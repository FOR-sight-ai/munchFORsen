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
# With Python
uv run uvicorn proxy:app --host 0.0.0.0 --port 8000

# With the executable
./dist/proxy --host 0.0.0.0 --port 8000
```


## Acknowledgement
This project received funding from the French ”IA Cluster” program within the Artificial and Natural Intelligence Toulouse Institute (ANITI) and from the "France 2030" program within IRT Saint Exupery. The authors gratefully acknowledge the support of the FOR projects.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
