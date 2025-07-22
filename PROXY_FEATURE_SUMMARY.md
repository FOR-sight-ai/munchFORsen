# Corporate Proxy Support - Feature Summary

## Overview
Added comprehensive corporate proxy support to the MunchFORsen proxy server, allowing all HTTP requests to be routed through corporate firewalls and proxy servers.

## Changes Made

### 1. Core Implementation (`proxy.py`)

#### New Global Variables
- `PROXY_URL`: Stores the proxy server URL
- `PROXY_AUTH`: Stores proxy authentication credentials as a tuple

#### New Functions
- `create_http_client(timeout=30.0)`: Creates httpx.AsyncClient with proxy configuration
- `parse_proxy_auth(proxy_auth_str)`: Parses "username:password" format for proxy authentication

#### Modified Functions
- Updated all `httpx.AsyncClient()` calls to use `create_http_client()`
- Modified `run_server()` to handle proxy configuration
- Modified `run_replay()` to handle proxy configuration
- Updated argument parser to include proxy options

#### HTTP Client Updates
All HTTP requests now support proxy configuration:
- Token requests (`request_token()`)
- Request replay (`replay_request_from_file()`)
- Main proxy functionality (`proxy()` endpoint)

### 2. Command Line Interface

#### New Arguments (Server Mode)
- `--proxy-url URL`: Corporate proxy URL (HTTP/HTTPS)
- `--proxy-auth USER:PASS`: Proxy authentication credentials

#### New Arguments (Replay Mode)
- `--proxy-url URL`: Corporate proxy URL (HTTP/HTTPS)
- `--proxy-auth USER:PASS`: Proxy authentication credentials

#### Updated Help Text
- Added proxy examples to main help
- Added proxy examples to server mode help
- Added proxy examples to replay mode help

### 3. Documentation (`README.md`)

#### New Features Section
- Added "Corporate proxy support with optional authentication" to feature list

#### New Usage Examples
- Basic proxy usage without authentication
- Proxy usage with authentication
- HTTPS proxy support
- Docker examples with proxy

#### New Dedicated Section
- "Corporate Proxy Support" section with comprehensive documentation
- Supported proxy types
- Behavior description
- Security notes

## Features

### Proxy Types Supported
- HTTP proxies (`http://proxy.company.com:8080`)
- HTTPS proxies (`https://proxy.company.com:8080`)
- Authenticated proxies (username:password)

### Authentication
- Supports username:password format
- Handles passwords containing colons
- Validates authentication format
- Provides clear error messages

### Error Handling
- Validates proxy authentication format
- Warns when auth is specified without proxy URL
- Graceful error handling with informative messages
- Exits with appropriate error codes

### Integration
- Works with all existing features (token requests, header merging, etc.)
- Available in both server and replay modes
- Global configuration affects all HTTP clients
- No breaking changes to existing functionality

## Usage Examples

### Server Mode
```bash
# Basic proxy
python proxy.py server --proxy-url http://proxy.company.com:8080

# With authentication
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password

# HTTPS proxy
python proxy.py server --proxy-url https://secure-proxy.company.com:8080 --proxy-auth username:password
```

### Replay Mode
```bash
# Basic proxy
python proxy.py replay log_file.json --proxy-url http://proxy.company.com:8080

# With authentication
python proxy.py replay log_file.json --proxy-url http://proxy.company.com:8080 --proxy-auth username:password
```

### Test Proxy Connectivity
```bash
# Test basic proxy connectivity
python proxy.py test-proxy --proxy-url http://proxy.company.com:8080

# Test proxy with authentication
python proxy.py test-proxy --proxy-url http://proxy.company.com:8080 --proxy-auth username:password

# Test HTTPS proxy with domain authentication
python proxy.py test-proxy --proxy-url https://proxy.company.com:8080 --proxy-auth "DOMAIN\\username:password"
```

### Combined with Other Features
```bash
# Proxy + token request + header merging
python proxy.py server \
  --proxy-url http://proxy.company.com:8080 \
  --proxy-auth username:password \
  --token-request token_config.json \
  --merge-header headers.json \
  --log

# Server with proxy debugging enabled
python proxy.py server \
  --proxy-url http://proxy.company.com:8080 \
  --proxy-auth username:password \
  --proxy-debug
```

## Security Considerations

1. **Command Line Arguments**: Proxy credentials are visible in process lists
2. **Recommendation**: Use environment variables or configuration files in production
3. **Credential Storage**: Keep proxy authentication secure
4. **Network Security**: Ensure proxy connections are encrypted when possible

## Recent Updates

### 2025-07-22 - 407 Authentication Error Fix and Troubleshooting
- **Issue**: Fixed 407 Authentication Required error with corporate proxies
- **Root Cause**: httpx requires proxy credentials to be embedded in the proxy URL, not passed as separate auth parameter
- **Changes**:
  - Fixed proxy authentication by embedding credentials in proxy URL format
  - Added comprehensive error handling for proxy authentication failures
  - Added `--proxy-debug` flag for detailed error information
  - Added `test-proxy` command to test proxy connectivity and authentication
  - Created comprehensive `PROXY_TROUBLESHOOTING.md` guide
- **Impact**: Corporate proxy authentication now works correctly
- **Testing**: Verified proxy authentication with embedded credentials format

### 2025-07-22 - httpx Proxy Parameter Fix
- **Issue**: Fixed incorrect parameter name for httpx AsyncClient proxy configuration
- **Change**: Changed `client_kwargs["proxies"]` to `client_kwargs["proxy"]` in `create_http_client()` function
- **Impact**: Proxy functionality now works correctly with httpx library
- **Testing**: Verified HTTP/HTTPS proxy support with and without authentication

## Testing

The implementation has been tested for:
- ✅ Proxy URL configuration
- ✅ Proxy authentication parsing
- ✅ Error handling for invalid formats
- ✅ Warning messages for misconfigurations
- ✅ Integration with existing features
- ✅ Server startup with proxy configuration
- ✅ Help text and documentation
- ✅ Backward compatibility
- ✅ httpx AsyncClient proxy parameter configuration
- ✅ HTTP and HTTPS proxy support
- ✅ Proxy with and without authentication
- ✅ 407 Authentication Required error handling
- ✅ Proxy debug mode functionality
- ✅ Proxy connectivity testing command

## Backward Compatibility

- ✅ No breaking changes to existing functionality
- ✅ All existing command line options work unchanged
- ✅ Default behavior (no proxy) remains the same
- ✅ Existing configuration files and scripts continue to work