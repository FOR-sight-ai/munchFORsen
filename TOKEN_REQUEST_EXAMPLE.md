# Token Request Feature

The `--token-request` option allows the proxy to automatically obtain an authentication token before making requests. This is useful for APIs that require OAuth2 or similar token-based authentication.

## How it works

1. Before each proxied request, the proxy makes a token request using the configuration provided in a JSON file
2. The obtained token is added to the `Authorization` header as `Bearer {token}`
3. Any existing authorization header is replaced with the new token

## Configuration File Format

The token request configuration is provided as a JSON file with the following structure:

```json
{
  "url": "https://your-token-endpoint.com/oauth/token",
  "method": "POST",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded"
  },
  "data": {
    "grant_type": "client_credentials",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "scope": "your_scope"
  },
  "token_field": "access_token"
}
```

### Configuration Fields

- **url** (required): The endpoint URL for token requests
- **method** (optional): HTTP method, defaults to "POST"
- **headers** (optional): Headers to send with the token request
- **data** (optional): Data to send with the token request (form data for POST requests)
- **token_field** (optional): Field name in the response containing the token, defaults to "access_token"

## Usage Examples

### Server Mode
```bash
# Start server with token request enabled
python proxy.py server --token-request token_config.json

# Combined with other options
python proxy.py server --token-request token_config.json --log --port 9000
```

### Replay Mode
```bash
# Replay a request with token request enabled
python proxy.py replay saved_request.json --token-request token_config.json

# Combined with other options
python proxy.py replay saved_request.json --token-request token_config.json --output json
```

## Example: OAuth2 Client Credentials Flow

This example shows how to configure the proxy for a typical OAuth2 client credentials flow:

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

This corresponds to the following curl command:
```bash
curl -X POST \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials" \
     -d "client_id=your_client_id_here" \
     -d "client_secret=your_client_secret_here" \
     -d "scope=api:read api:write" \
     "https://auth.example.com/oauth/token"
```

## Environment Variables

You can use environment variables in your configuration by referencing them with `$VARIABLE_NAME` syntax:

```json
{
  "url": "$TOKEN_ENDPOINT",
  "data": {
    "grant_type": "client_credentials",
    "client_id": "$SP_CLIENT_ID",
    "client_secret": "$SP_CLIENT_SECRET",
    "scope": "$OAUTH_SCOPE"
  }
}
```

Note: Environment variable substitution is handled by your shell or application, not by the proxy itself.

## Error Handling

If the token request fails:
- In server mode: The proxy returns a 500 error with details about the token request failure
- In replay mode: The replay fails with an error message containing token request failure details

Common error scenarios:
- Token endpoint is unreachable
- Invalid credentials
- Token field not found in response
- Invalid JSON response from token endpoint