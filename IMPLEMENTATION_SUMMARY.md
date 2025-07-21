# Token Request Feature Implementation Summary

## Overview
Successfully implemented the `--token-request` option that allows the proxy to automatically obtain authentication tokens before making requests. The token is added to the `Authorization` header as `Bearer {token}`, replacing any existing authorization.

## Changes Made

### 1. Core Functionality
- **Added `load_token_request_config()`**: Loads and validates token request configuration from JSON files
- **Added `request_token()`**: Makes HTTP requests to obtain tokens using the provided configuration
- **Added global variable `TOKEN_REQUEST_CONFIG`**: Stores the token request configuration

### 2. Command Line Interface
- **Added `--token-request` argument** to both server and replay parsers
- **Updated help text and examples** to include the new option
- **Enhanced argument validation** with proper error handling

### 3. Server Mode Integration
- **Modified `run_server()`** to load and validate token request configuration
- **Updated proxy endpoint** to request tokens before each proxied request
- **Added error handling** for token request failures (returns 500 with details)

### 4. Replay Mode Integration
- **Modified `replay_request_from_file()`** to accept token request configuration
- **Updated `run_replay()`** to load and pass token configuration
- **Added token request support** to replay functionality

### 5. Documentation
- **Updated README.md** with comprehensive token request documentation
- **Created example configuration files** showing OAuth2 client credentials flow
- **Added detailed usage examples** and security notes
- **Created TOKEN_REQUEST_EXAMPLE.md** with extensive documentation

## Configuration File Format

The token request configuration uses a JSON file with the following structure:

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

## Key Features

### 1. Flexible Configuration
- Supports any HTTP method (defaults to POST)
- Configurable headers for token requests
- Supports both form data and JSON data
- Configurable token field name in response

### 2. OAuth2 Compatibility
- Designed for OAuth2 client credentials flow
- Supports `application/x-www-form-urlencoded` content type
- Compatible with standard OAuth2 parameters

### 3. Error Handling
- Comprehensive error messages for configuration issues
- Detailed error reporting for token request failures
- Graceful handling of network timeouts and errors

### 4. Security Considerations
- No credentials stored in code
- Configuration files can use environment variables
- Clear security warnings in documentation

## Usage Examples

### Server Mode
```bash
# Basic usage
python proxy.py server --token-request token_config.json

# Combined with other features
python proxy.py server --token-request token_config.json --log --port 9000
```

### Replay Mode
```bash
# Basic replay with token request
python proxy.py replay saved_request.json --token-request token_config.json

# Combined with other options
python proxy.py replay saved_request.json --token-request token_config.json --output json
```

## Testing
- ✅ Configuration loading and validation
- ✅ Token request functionality
- ✅ Server startup with and without token configuration
- ✅ Command line argument parsing
- ✅ Help text and documentation
- ✅ Backward compatibility (existing functionality unchanged)

## Files Modified
- `proxy.py`: Core implementation
- `README.md`: Updated documentation
- `example_token_config.json`: Example configuration
- `example_token_config_env.json`: Example with environment variables
- `TOKEN_REQUEST_EXAMPLE.md`: Detailed documentation

## Curl Command Equivalent
The implementation supports the exact curl command pattern requested:

```bash
curl -X POST \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     -d "client_id=$SP_CLIENT_ID" \
     -d "client_secret=$SP_CLIENT_SECRET" \
     -d "scope=$OAUTH_SCOPE" \
     "$TOKEN_ENDPOINT"
```

This translates to the JSON configuration format, allowing users to easily convert their existing curl commands to the proxy's token request configuration.