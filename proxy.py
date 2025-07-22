from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import asyncio
import random
import copy
import os
import json
from datetime import datetime
import uuid
import argparse
import sys
import platform

app = FastAPI()

# Default target URL
DEFAULT_TARGET_URL = "https://openrouter.ai/api/v1/chat/completions"
TARGET_URL = DEFAULT_TARGET_URL

# Global flag for content flattening
FLATTEN_CONTENT = False

# Global flags
NO_TOOL_ROLES = False
ENABLE_LOGGING = False

# Global headers to merge from file
MERGE_HEADERS = {}

# Global token request configuration
TOKEN_REQUEST_CONFIG = None

# Global proxy configuration
PROXY_URL = None
PROXY_AUTH = None
PROXY_DEBUG = False

def get_logs_directory():
    """Get the appropriate logs directory for the current OS"""
    system = platform.system()
    
    if system == "Windows":
        # Windows: Use %USERPROFILE%\AppData\Local\Proxy\logs
        base_dir = os.path.expanduser("~\\AppData\\Local\\Proxy")
    else:
        # macOS/Linux: Use ~/.local/share/proxy
        base_dir = os.path.expanduser("~/.local/share/proxy")
    
    logs_dir = os.path.join(base_dir, "logs")
    return logs_dir

LOG_DIR = get_logs_directory()
os.makedirs(LOG_DIR, exist_ok=True)

def create_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """
    Create an httpx AsyncClient with proxy configuration if available.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Configured httpx AsyncClient instance
    """
    client_kwargs = {"timeout": timeout}
    
    if PROXY_URL:
        # For proxy authentication, we need to embed credentials in the proxy URL
        if PROXY_AUTH:
            username, password = PROXY_AUTH
            # Parse the proxy URL to inject credentials
            if "://" in PROXY_URL:
                scheme, rest = PROXY_URL.split("://", 1)
                proxy_url_with_auth = f"{scheme}://{username}:{password}@{rest}"
            else:
                proxy_url_with_auth = f"{username}:{password}@{PROXY_URL}"
            client_kwargs["proxy"] = proxy_url_with_auth
        else:
            client_kwargs["proxy"] = PROXY_URL
    
    return httpx.AsyncClient(**client_kwargs)

async def test_proxy_connection(proxy_url: str, proxy_auth: tuple = None) -> dict:
    """
    Test proxy connection by making a simple HTTP request.
    
    Args:
        proxy_url: Proxy URL to test
        proxy_auth: Optional tuple of (username, password) for authentication
        
    Returns:
        Dictionary with test results
    """
    test_url = "https://httpbin.org/ip"
    result = {
        "success": False,
        "error": None,
        "response_time": None,
        "status_code": None,
        "proxy_url": proxy_url
    }
    
    try:
        import time
        start_time = time.time()
        
        # Create client with proxy configuration
        client_kwargs = {"timeout": 10.0}
        
        if proxy_auth:
            username, password = proxy_auth
            if "://" in proxy_url:
                scheme, rest = proxy_url.split("://", 1)
                proxy_url_with_auth = f"{scheme}://{username}:{password}@{rest}"
            else:
                proxy_url_with_auth = f"{username}:{password}@{proxy_url}"
            client_kwargs["proxy"] = proxy_url_with_auth
        else:
            client_kwargs["proxy"] = proxy_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(test_url)
            
        end_time = time.time()
        result["response_time"] = round((end_time - start_time) * 1000, 2)  # ms
        result["status_code"] = response.status_code
        result["success"] = response.status_code == 200
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                result["origin_ip"] = response_data.get("origin", "unknown")
            except:
                pass
                
    except httpx.ProxyError as e:
        result["error"] = f"Proxy error: {str(e)}"
        if "407" in str(e) or "Authentication Required" in str(e):
            result["error"] = "Proxy authentication failed (407). Check your credentials."
    except httpx.TimeoutException as e:
        result["error"] = f"Timeout error: {str(e)}"
    except Exception as e:
        result["error"] = f"Connection error: {str(e)}"
    
    return result

def parse_proxy_auth(proxy_auth_str: str) -> tuple:
    """
    Parse proxy authentication string in format 'username:password'.
    
    Args:
        proxy_auth_str: Authentication string in format 'username:password'
        
    Returns:
        Tuple of (username, password)
        
    Raises:
        ValueError: If the format is invalid
    """
    if not proxy_auth_str or ':' not in proxy_auth_str:
        raise ValueError("Proxy authentication must be in format 'username:password'")
    
    parts = proxy_auth_str.split(':', 1)  # Split only on first colon to handle passwords with colons
    if len(parts) != 2:
        raise ValueError("Proxy authentication must be in format 'username:password'")
    
    username, password = parts
    if not username or not password:
        raise ValueError("Both username and password must be non-empty")
    
    return (username, password)

def load_merge_headers(file_path: str) -> dict:
    """
    Load headers from a JSON file to merge with requests.
    
    Args:
        file_path: Path to the JSON file containing headers
        
    Returns:
        Dictionary of headers to merge
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        ValueError: If the file doesn't contain a valid header dictionary
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Header file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            headers = json.load(f)
        
        if not isinstance(headers, dict):
            raise ValueError("Header file must contain a JSON object (dictionary)")
        
        # Validate that all values are strings (header values must be strings)
        for key, value in headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(f"All header keys and values must be strings. Invalid entry: {key}: {value}")
        
        return headers
    
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in header file {file_path}: {e.msg}", e.doc, e.pos)

def load_token_request_config(file_path: str) -> dict:
    """
    Load token request configuration from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing token request parameters
        
    Returns:
        Dictionary containing token request configuration
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        ValueError: If the file doesn't contain required fields
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Token request config file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not isinstance(config, dict):
            raise ValueError("Token request config file must contain a JSON object (dictionary)")
        
        # Validate required fields
        if 'url' not in config:
            raise ValueError("Token request config must contain 'url' field")
        
        # Set defaults for optional fields
        config.setdefault('method', 'POST')
        config.setdefault('headers', {})
        config.setdefault('data', {})
        config.setdefault('token_field', 'access_token')  # Default field name for token in response
        
        return config
    
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in token request config file {file_path}: {e.msg}", e.doc, e.pos)

async def request_token(config: dict) -> str:
    """
    Make a token request using the provided configuration.
    
    Args:
        config: Dictionary containing token request configuration
        
    Returns:
        The access token string
        
    Raises:
        Exception: If token request fails or token is not found in response
    """
    try:
        async with create_http_client(timeout=30.0) as client:
            # Prepare request parameters
            method = config.get('method', 'POST').upper()
            url = config['url']
            headers = config.get('headers', {})
            data = config.get('data', {})
            
            # Make the request
            if method == 'POST':
                # For OAuth2 token requests, typically use form data
                if 'Content-Type' not in headers and 'content-type' not in headers:
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
                
                if headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'):
                    response = await client.post(url, data=data, headers=headers)
                else:
                    response = await client.post(url, json=data, headers=headers)
            elif method == 'GET':
                response = await client.get(url, params=data, headers=headers)
            else:
                response = await client.request(method, url, json=data, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                raise Exception(f"Token request failed with status {response.status_code}: {response.text}")
            
            # Parse response
            try:
                response_data = response.json()
            except Exception:
                raise Exception(f"Token response is not valid JSON: {response.text}")
            
            # Extract token from response
            token_field = config.get('token_field', 'access_token')
            if token_field not in response_data:
                raise Exception(f"Token field '{token_field}' not found in response. Available fields: {list(response_data.keys())}")
            
            token = response_data[token_field]
            if not token:
                raise Exception(f"Token field '{token_field}' is empty in response")
            
            # If token is a complex object, try to convert it to JSON string
            if isinstance(token, (dict, list)):
                return json.dumps(token)
            
            return str(token)
            
    except httpx.TimeoutException as e:
        raise Exception(f"Token request timeout: {e}")
    except httpx.RequestError as e:
        raise Exception(f"Token request error: {e}")
    except Exception as e:
        if "Token request failed" in str(e) or "Token field" in str(e) or "Token response" in str(e):
            raise  # Re-raise our custom exceptions
        raise Exception(f"Unexpected error during token request: {e}")

def merge_headers_with_request(request_headers: dict, merge_headers: dict) -> dict:
    """
    Merge headers from file with request headers, replacing existing ones.
    
    Args:
        request_headers: Original headers from the request
        merge_headers: Headers to merge from file
        
    Returns:
        Dictionary with merged headers (merge_headers take precedence)
    """
    # Start with a copy of request headers
    merged = dict(request_headers)
    
    # Add/replace with headers from file (case-insensitive matching)
    for merge_key, merge_value in merge_headers.items():
        # Check if header already exists (case-insensitive)
        existing_key = None
        for req_key in merged.keys():
            if req_key.lower() == merge_key.lower():
                existing_key = req_key
                break
        
        # Remove existing header if found, then add the new one
        if existing_key:
            del merged[existing_key]
        
        merged[merge_key] = merge_value
    
    return merged

def flatten_content_in_body(body: dict) -> dict:
    """
    Flatten content fields in messages if they are lists with single text elements.
    
    Args:
        body: The request body dictionary
        
    Returns:
        Modified body with flattened content fields
    """
    if not isinstance(body, dict):
        return body
    
    # Make a deep copy to avoid modifying the original
    flattened_body = copy.deepcopy(body)
    
    # Check if this looks like a chat completion request with messages
    if "messages" in flattened_body and isinstance(flattened_body["messages"], list):
        for message in flattened_body["messages"]:
            if isinstance(message, dict) and "content" in message:
                content = message["content"]
                
                # Check if content is a list with exactly one element
                if (isinstance(content, list) and 
                    len(content) == 1 and 
                    isinstance(content[0], dict) and 
                    content[0].get("type") == "text" and 
                    "text" in content[0]):
                    
                    # Replace the content with just the text value
                    message["content"] = content[0]["text"]
    
    return flattened_body

def replace_tool_roles_in_body(body: dict) -> dict:
    """
    Replace "tool-call" and "tool-response" roles with "user" in messages.
    
    Args:
        body: The request body dictionary
        
    Returns:
        Modified body with tool roles replaced
    """
    if not isinstance(body, dict):
        return body
    
    # Make a deep copy to avoid modifying the original
    modified_body = copy.deepcopy(body)
    
    # Check if this looks like a chat completion request with messages
    if "messages" in modified_body and isinstance(modified_body["messages"], list):
        for message in modified_body["messages"]:
            if isinstance(message, dict) and "role" in message:
                role = message["role"]
                
                # Replace tool-call and tool-response roles with user
                if role in ["tool-call", "tool-response"]:
                    message["role"] = "user"
    
    return modified_body

async def save_request_to_file(path: str, method: str, headers: dict, body: dict):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "path": path,
        "method": method,
        "headers": dict(headers),
        "body": body
    }
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.json"
    filepath = os.path.join(LOG_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)

async def replay_request_from_file(filepath: str, target_url: str = None, flatten_content: bool = False, no_tool_roles: bool = False, merge_headers: dict = None, token_request_config: dict = None):
    """Replay a request from a saved log file and return detailed results"""
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"File not found: {filepath}",
                "details": "The specified request file does not exist"
            }
        
        # Load the request data
        with open(filepath, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        
        # Extract request details
        path = log_data.get("path", "")
        method = log_data.get("method", "POST")
        headers = log_data.get("headers", {})
        body = log_data.get("body", {})
        original_timestamp = log_data.get("timestamp", "Unknown")
        
        # Use provided target URL or default
        url_to_use = target_url or TARGET_URL
        
        # Apply content flattening if requested
        if flatten_content:
            body = flatten_content_in_body(body)
        
        # Apply tool role replacement if requested
        if no_tool_roles:
            body = replace_tool_roles_in_body(body)
        
        # Merge headers from file if provided
        if merge_headers:
            headers = merge_headers_with_request(headers, merge_headers)
        
        # Filter headers - only keep essential ones
        filtered_headers = {}
        essential_headers = {
            'authorization', 'content-type', 'accept', 'user-agent',
            'x-stainless-lang', 'x-stainless-package-version', 'x-stainless-os',
            'x-stainless-arch', 'x-stainless-runtime', 'x-stainless-runtime-version',
            'x-stainless-async', 'x-stainless-retry-count', 'x-stainless-read-timeout',
            'ocp-apim-subscription-key', 'trustnest-apim-subscription-key'
        }
        
        for header_name, header_value in headers.items():
            if header_name.lower() in essential_headers:
                filtered_headers[header_name] = header_value
        
        # Request token if configured
        if token_request_config:
            try:
                token = await request_token(token_request_config)
                # Replace any existing authorization header with the new token
                # Remove existing authorization headers (case-insensitive)
                filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'authorization'}
                # Add the new authorization header
                filtered_headers['Authorization'] = f"Bearer {token}"
            except Exception as e:
                return {
                    "success": False,
                    "error": "Token request failed",
                    "details": str(e),
                    "replay_info": {
                        "original_timestamp": original_timestamp,
                        "replay_timestamp": datetime.utcnow().isoformat(),
                        "file_path": filepath
                    }
                }
        
        # Perform the request
        start_time = datetime.utcnow()
        try:
            async with create_http_client(timeout=30.0) as client:
                if method.upper() == "POST":
                    response = await client.post(url_to_use, json=body, headers=filtered_headers)
                elif method.upper() == "GET":
                    response = await client.get(url_to_use, headers=filtered_headers)
                else:
                    response = await client.request(method, url_to_use, json=body, headers=filtered_headers)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Parse response
            try:
                response_json = response.json()
            except Exception as json_error:
                response_json = {
                    "error": "Invalid JSON response", 
                    "content": response.text,
                    "json_parse_error": str(json_error)
                }
            
            return {
                "success": True,
                "replay_info": {
                    "original_timestamp": original_timestamp,
                    "replay_timestamp": datetime.utcnow().isoformat(),
                    "response_time_seconds": response_time,
                    "file_path": filepath
                },
                "request": {
                    "method": method,
                    "path": path,
                    "url": url_to_use,
                    "headers": filtered_headers,
                    "body": body
                },
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_json
                }
            }
            
        except httpx.TimeoutException as e:
            return {
                "success": False,
                "error": "Request timeout",
                "details": str(e),
                "replay_info": {
                    "original_timestamp": original_timestamp,
                    "replay_timestamp": datetime.utcnow().isoformat(),
                    "file_path": filepath
                }
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": "Request error",
                "details": str(e),
                "replay_info": {
                    "original_timestamp": original_timestamp,
                    "replay_timestamp": datetime.utcnow().isoformat(),
                    "file_path": filepath
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error during request",
                "details": str(e),
                "replay_info": {
                    "original_timestamp": original_timestamp,
                    "replay_timestamp": datetime.utcnow().isoformat(),
                    "file_path": filepath
                }
            }
            
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "Invalid JSON in log file",
            "details": str(e),
            "file_path": filepath
        }
    except Exception as e:
        return {
            "success": False,
            "error": "Error reading log file",
            "details": str(e),
            "file_path": filepath
        }

@app.post("/{full_path:path}")
async def proxy(full_path: str, request: Request):
    try:
        incoming_body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    incoming_headers = dict(request.headers)

    # Merge headers from file if configured
    if MERGE_HEADERS:
        incoming_headers = merge_headers_with_request(incoming_headers, MERGE_HEADERS)

    # Save request to file if logging is enabled
    if ENABLE_LOGGING:
        await save_request_to_file(full_path, request.method, incoming_headers, incoming_body)

    # Apply content flattening if enabled
    body_to_send = incoming_body
    if FLATTEN_CONTENT:
        body_to_send = flatten_content_in_body(body_to_send)
    
    # Apply tool role replacement if enabled
    if NO_TOOL_ROLES:
        body_to_send = replace_tool_roles_in_body(body_to_send)

    # Filter headers - only keep essential ones for OpenRouter API
    filtered_headers = {}
    essential_headers = {
        'authorization', 'content-type', 'accept', 'user-agent',
        'x-stainless-lang', 'x-stainless-package-version', 'x-stainless-os',
        'x-stainless-arch', 'x-stainless-runtime', 'x-stainless-runtime-version',
        'x-stainless-async', 'x-stainless-retry-count', 'x-stainless-read-timeout',
        'ocp-apim-subscription-key', 'trustnest-apim-subscription-key'
    }
    
    for header_name, header_value in incoming_headers.items():
        if header_name.lower() in essential_headers:
            filtered_headers[header_name] = header_value

    # Request token if configured
    if TOKEN_REQUEST_CONFIG:
        try:
            token = await request_token(TOKEN_REQUEST_CONFIG)
            # Replace any existing authorization header with the new token
            # Remove existing authorization headers (case-insensitive)
            filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'authorization'}
            # Add the new authorization header
            filtered_headers['Authorization'] = f"Bearer {token}"
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Token request failed: {str(e)}"})

    try:
        async with create_http_client(timeout=30.0) as client:
            response = await client.post(TARGET_URL, json=body_to_send, headers=filtered_headers)
    except httpx.ProxyError as e:
        if "407" in str(e) or "Authentication Required" in str(e):
            error_msg = "Proxy authentication failed (407). Please check your proxy credentials."
            if PROXY_DEBUG:
                error_msg += f" Details: {str(e)}"
            return JSONResponse(status_code=407, content={"error": error_msg})
        else:
            error_msg = f"Proxy error: {str(e)}"
            return JSONResponse(status_code=502, content={"error": error_msg})
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        if PROXY_DEBUG:
            error_msg += f" (Proxy URL: {PROXY_URL})"
        return JSONResponse(status_code=502, content={"error": error_msg})

    try:
        response_json = response.json()
    except Exception:
        # Si la réponse n'est pas du JSON, retourner le texte brut
        response_json = {"error": "Invalid JSON response", "content": response.text}

    if response.status_code == 200:
        return JSONResponse(status_code=200, content=response_json)
    else:
        return JSONResponse(status_code=response.status_code, content=response_json)
    
def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        prog='proxy.py',
        description='FastAPI Proxy Server with Request Logging and Replay Capabilities',
        epilog=f'''
Examples:
  %(prog)s                                    # Start server with default settings
  %(prog)s server --port 9000                # Start server on port 9000
  %(prog)s server --target-url https://api.openai.com/v1/chat/completions
  %(prog)s server --flatten-content          # Start server with content flattening enabled
  %(prog)s server --no-tool-roles            # Start server with tool role replacement enabled
  %(prog)s server --log                      # Start server with request logging enabled
  %(prog)s server --merge-header headers.json # Start server with header merging from JSON file
  %(prog)s server --token-request token.json  # Start server with token request enabled
  %(prog)s server --proxy-url http://proxy.company.com:8080  # Start server with corporate proxy
  %(prog)s server --proxy-url http://proxy.company.com:8080 --proxy-auth user:pass  # With proxy auth
  %(prog)s replay <log_file_path>             # Replay a saved request
  %(prog)s replay <log_file_path> --output json --target-url https://test-api.com
  %(prog)s replay <log_file_path> --flatten-content  # Replay with content flattening
  %(prog)s replay <log_file_path> --no-tool-roles    # Replay with tool role replacement
  %(prog)s --help                            # Show this help message
  %(prog)s server --help                     # Show server mode help
  %(prog)s replay --help                     # Show replay mode help

Note: Log files are saved in: {LOG_DIR}
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add global option to show logs directory
    parser.add_argument(
        "--logs-dir", 
        action='store_true',
        help="Show the directory where log files are saved and exit"
    )
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(
        dest='mode', 
        help='Operation mode - use "server" to run proxy or "replay" to replay saved requests',
        metavar='{server,replay}'
    )
    
    # Server mode
    server_parser = subparsers.add_parser(
        'server', 
        help='Run the proxy server to intercept and log requests',
        description='Start a FastAPI proxy server that forwards requests to a target URL while logging all requests to files',
        epilog='''
Server Mode Examples:
  python proxy.py server                     # Start with defaults (port 8000, OpenRouter API)
  python proxy.py server --port 9000         # Start on port 9000
  python proxy.py server --host 127.0.0.1    # Bind to localhost only
  python proxy.py server --target-url https://api.openai.com/v1/chat/completions
  python proxy.py server --flatten-content   # Enable content flattening for single-text arrays
  python proxy.py server --no-tool-roles     # Enable tool role replacement
  python proxy.py server --log               # Enable request logging
  python proxy.py server --merge-header headers.json  # Merge headers from JSON file
  python proxy.py server --token-request token.json   # Enable token request
  python proxy.py server --proxy-url http://proxy.company.com:8080  # Use corporate proxy
  python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth user:pass  # With proxy auth
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    server_parser.add_argument(
        "--target-url", 
        type=str, 
        default=DEFAULT_TARGET_URL,
        help=f"Target URL to proxy requests to. All incoming requests will be forwarded to this URL. (default: {DEFAULT_TARGET_URL})",
        metavar='URL'
    )
    server_parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="Host/IP address to bind the server to. Use 0.0.0.0 for all interfaces or 127.0.0.1 for localhost only (default: 0.0.0.0)",
        metavar='HOST'
    )
    server_parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port number to run the server on (default: 8000)",
        metavar='PORT'
    )
    server_parser.add_argument(
        "--flatten-content", 
        action='store_true',
        help="Flatten content fields in messages: if content is a list with a single text element, replace it with just the text string"
    )
    server_parser.add_argument(
        "--no-tool-roles", 
        action='store_true',
        help="Replace 'tool-call' and 'tool-response' roles with 'user' in messages"
    )
    server_parser.add_argument(
        "--log", 
        action='store_true',
        help="Enable request logging to files (disabled by default)"
    )
    server_parser.add_argument(
        "--merge-header", 
        type=str,
        help="Path to JSON file containing headers to merge with each request. Headers from file will replace existing headers if they have the same name (case-insensitive). Example: --merge-header headers.json",
        metavar='FILE'
    )
    server_parser.add_argument(
        "--token-request", 
        type=str,
        help="Path to JSON file containing parameters for making a token request. The obtained token will be used in Authorization header as 'Bearer {token}', replacing any existing authorization. Example: --token-request token_config.json",
        metavar='FILE'
    )
    server_parser.add_argument(
        "--proxy-url", 
        type=str,
        help="Corporate proxy URL to use for all HTTP requests. Supports HTTP and HTTPS proxies. Example: --proxy-url http://proxy.company.com:8080 or --proxy-url https://proxy.company.com:8080",
        metavar='URL'
    )
    server_parser.add_argument(
        "--proxy-auth", 
        type=str,
        help="Proxy authentication in the format 'username:password'. Use with --proxy-url for authenticated proxies. Example: --proxy-auth myuser:mypass",
        metavar='USER:PASS'
    )
    server_parser.add_argument(
        "--proxy-debug",
        action="store_true",
        help="Enable detailed proxy debugging information in error messages"
    )
    
    # Replay mode
    replay_parser = subparsers.add_parser(
        'replay', 
        help='Replay a previously saved request from log files',
        description='Replay HTTP requests from previously saved log files with detailed error reporting and timing information',
        epilog=f'''
Replay Mode Examples:
  python proxy.py replay <log_file_path>                     # Replay specific request
  python proxy.py replay <log_file_path> --output json       # Get JSON output
  python proxy.py replay <log_file_path> --target-url https://test-api.com  # Override target URL
  python proxy.py replay <log_file_path> --flatten-content   # Enable content flattening during replay
  python proxy.py replay <log_file_path> --no-tool-roles     # Enable tool role replacement during replay
  python proxy.py replay <log_file_path> --merge-header headers.json  # Merge headers from JSON file during replay
  python proxy.py replay <log_file_path> --token-request token.json   # Enable token request during replay
  python proxy.py replay <log_file_path> --proxy-url http://proxy.company.com:8080  # Use corporate proxy during replay
  python proxy.py replay <log_file_path> --proxy-url http://proxy.company.com:8080 --proxy-auth user:pass  # With proxy auth

Log files location: {LOG_DIR}
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    replay_parser.add_argument(
        'file', 
        type=str, 
        help='Path to the saved request file (JSON format) that you want to replay. These files are created automatically when using the server mode.',
        metavar='LOG_FILE'
    )
    replay_parser.add_argument(
        "--target-url", 
        type=str, 
        help="Override the target URL for the replay. If not specified, uses the default target URL. Useful for testing the same request against different endpoints.",
        metavar='URL'
    )
    replay_parser.add_argument(
        "--output", 
        type=str, 
        choices=['json', 'pretty'],
        default='pretty',
        help="Output format: 'pretty' for human-readable format with emojis and formatting, 'json' for raw JSON output suitable for parsing (default: pretty)",
        metavar='FORMAT'
    )
    replay_parser.add_argument(
        "--flatten-content", 
        action='store_true',
        help="Flatten content fields in messages: if content is a list with a single text element, replace it with just the text string"
    )
    replay_parser.add_argument(
        "--no-tool-roles", 
        action='store_true',
        help="Replace 'tool-call' and 'tool-response' roles with 'user' in messages"
    )
    replay_parser.add_argument(
        "--merge-header", 
        type=str,
        help="Path to JSON file containing headers to merge with the replayed request. Headers from file will replace existing headers if they have the same name (case-insensitive). Example: --merge-header headers.json",
        metavar='FILE'
    )
    replay_parser.add_argument(
        "--token-request", 
        type=str,
        help="Path to JSON file containing parameters for making a token request. The obtained token will be used in Authorization header as 'Bearer {token}', replacing any existing authorization. Example: --token-request token_config.json",
        metavar='FILE'
    )
    replay_parser.add_argument(
        "--proxy-url", 
        type=str,
        help="Corporate proxy URL to use for all HTTP requests. Supports HTTP and HTTPS proxies. Example: --proxy-url http://proxy.company.com:8080 or --proxy-url https://proxy.company.com:8080",
        metavar='URL'
    )
    replay_parser.add_argument(
        "--proxy-auth", 
        type=str,
        help="Proxy authentication in the format 'username:password'. Use with --proxy-url for authenticated proxies. Example: --proxy-auth myuser:mypass",
        metavar='USER:PASS'
    )
    replay_parser.add_argument(
        "--proxy-debug",
        action="store_true",
        help="Enable detailed proxy debugging information in error messages"
    )
    
    # Test proxy mode
    test_parser = subparsers.add_parser(
        'test-proxy',
        help='Test corporate proxy connectivity and authentication',
        description='Test if the corporate proxy configuration is working correctly',
        epilog='''
Test Proxy Examples:
  python proxy.py test-proxy --proxy-url http://proxy.company.com:8080
  python proxy.py test-proxy --proxy-url http://proxy.company.com:8080 --proxy-auth user:pass
  python proxy.py test-proxy --proxy-url https://proxy.company.com:8080 --proxy-auth "domain\\user:pass"
        '''
    )
    test_parser.add_argument(
        "--proxy-url",
        type=str,
        required=True,
        help="Corporate proxy URL to test. Example: --proxy-url http://proxy.company.com:8080",
        metavar='URL'
    )
    test_parser.add_argument(
        "--proxy-auth",
        type=str,
        help="Proxy authentication in the format 'username:password'. Example: --proxy-auth myuser:mypass",
        metavar='USER:PASS'
    )
    
    # If no arguments provided, default to server mode
    if len(sys.argv) == 1:
        sys.argv.append('server')
    
    return parser.parse_args()

def run_server(args):
    """Run the proxy server"""
    global TARGET_URL, FLATTEN_CONTENT, NO_TOOL_ROLES, ENABLE_LOGGING, MERGE_HEADERS, TOKEN_REQUEST_CONFIG, PROXY_URL, PROXY_AUTH, PROXY_DEBUG
    TARGET_URL = args.target_url
    FLATTEN_CONTENT = args.flatten_content
    NO_TOOL_ROLES = args.no_tool_roles
    ENABLE_LOGGING = args.log
    
    # Load merge headers if specified
    if hasattr(args, 'merge_header') and args.merge_header:
        try:
            MERGE_HEADERS = load_merge_headers(args.merge_header)
            print(f"Loaded {len(MERGE_HEADERS)} headers from: {args.merge_header}")
            for header_name in MERGE_HEADERS.keys():
                print(f"  - {header_name}")
        except Exception as e:
            print(f"Error loading merge headers from {args.merge_header}: {e}")
            sys.exit(1)
    
    # Load token request configuration if specified
    if hasattr(args, 'token_request') and args.token_request:
        try:
            TOKEN_REQUEST_CONFIG = load_token_request_config(args.token_request)
            print(f"Loaded token request configuration from: {args.token_request}")
            print(f"  - Token endpoint: {TOKEN_REQUEST_CONFIG['url']}")
            print(f"  - Method: {TOKEN_REQUEST_CONFIG.get('method', 'POST')}")
            print(f"  - Token field: {TOKEN_REQUEST_CONFIG.get('token_field', 'access_token')}")
        except Exception as e:
            print(f"Error loading token request configuration from {args.token_request}: {e}")
            sys.exit(1)
    
    # Configure proxy settings if specified
    if hasattr(args, 'proxy_url') and args.proxy_url:
        PROXY_URL = args.proxy_url
        print(f"Proxy URL configured: {PROXY_URL}")
        
        # Configure proxy authentication if specified
        if hasattr(args, 'proxy_auth') and args.proxy_auth:
            try:
                PROXY_AUTH = parse_proxy_auth(args.proxy_auth)
                print(f"Proxy authentication configured for user: {PROXY_AUTH[0]}")
            except ValueError as e:
                print(f"Error parsing proxy authentication: {e}")
                sys.exit(1)
    elif hasattr(args, 'proxy_auth') and args.proxy_auth:
        print("Warning: --proxy-auth specified without --proxy-url. Proxy authentication will be ignored.")
        print("Please specify --proxy-url along with --proxy-auth.")
    
    # Configure proxy debug mode
    if hasattr(args, 'proxy_debug') and args.proxy_debug:
        PROXY_DEBUG = True
        print("Proxy debug mode enabled")
    
    print(f"Starting proxy server...")
    print(f"Target URL: {TARGET_URL}")
    print(f"Content flattening: {'enabled' if FLATTEN_CONTENT else 'disabled'}")
    print(f"Tool role replacement: {'enabled' if NO_TOOL_ROLES else 'disabled'}")
    print(f"Request logging: {'enabled' if ENABLE_LOGGING else 'disabled'}")
    print(f"Header merging: {'enabled' if MERGE_HEADERS else 'disabled'}")
    print(f"Token request: {'enabled' if TOKEN_REQUEST_CONFIG else 'disabled'}")
    print(f"Corporate proxy: {'enabled' if PROXY_URL else 'disabled'}")
    if PROXY_URL:
        print(f"  - Proxy URL: {PROXY_URL}")
        print(f"  - Proxy auth: {'enabled' if PROXY_AUTH else 'disabled'}")
    print(f"Server will be available at: http://{args.host}:{args.port}")
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)

async def run_replay(args):
    """Run replay mode"""
    global PROXY_URL, PROXY_AUTH, PROXY_DEBUG
    
    print(f"Replaying request from: {args.file}")
    if args.flatten_content:
        print("Content flattening: enabled")
    if args.no_tool_roles:
        print("Tool role replacement: enabled")
    
    # Load merge headers if specified
    merge_headers = None
    if hasattr(args, 'merge_header') and args.merge_header:
        try:
            merge_headers = load_merge_headers(args.merge_header)
            print(f"Header merging: enabled ({len(merge_headers)} headers from {args.merge_header})")
            for header_name in merge_headers.keys():
                print(f"  - {header_name}")
        except Exception as e:
            print(f"Error loading merge headers from {args.merge_header}: {e}")
            return
    
    # Load token request configuration if specified
    token_request_config = None
    if hasattr(args, 'token_request') and args.token_request:
        try:
            token_request_config = load_token_request_config(args.token_request)
            print(f"Token request: enabled (endpoint: {token_request_config['url']})")
        except Exception as e:
            print(f"Error loading token request configuration from {args.token_request}: {e}")
            return
    
    # Configure proxy settings if specified
    if hasattr(args, 'proxy_url') and args.proxy_url:
        PROXY_URL = args.proxy_url
        print(f"Corporate proxy: enabled ({PROXY_URL})")
        
        # Configure proxy authentication if specified
        if hasattr(args, 'proxy_auth') and args.proxy_auth:
            try:
                PROXY_AUTH = parse_proxy_auth(args.proxy_auth)
                print(f"Proxy authentication: enabled (user: {PROXY_AUTH[0]})")
            except ValueError as e:
                print(f"Error parsing proxy authentication: {e}")
                return
    elif hasattr(args, 'proxy_auth') and args.proxy_auth:
        print("Warning: --proxy-auth specified without --proxy-url. Proxy authentication will be ignored.")
        print("Please specify --proxy-url along with --proxy-auth.")
    
    # Configure proxy debug mode
    if hasattr(args, 'proxy_debug') and args.proxy_debug:
        PROXY_DEBUG = True
        print("Proxy debug mode: enabled")
    
    print("-" * 50)
    
    result = await replay_request_from_file(args.file, args.target_url, args.flatten_content, args.no_tool_roles, merge_headers, token_request_config)
    
    if args.output == 'json':
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Pretty print format
        if result['success']:
            print(f"✅ Replay successful!")
            print(f"📁 File: {result['replay_info']['file_path']}")
            print(f"⏰ Original timestamp: {result['replay_info']['original_timestamp']}")
            print(f"🔄 Replay timestamp: {result['replay_info']['replay_timestamp']}")
            print(f"⚡ Response time: {result['replay_info']['response_time_seconds']:.3f}s")
            print(f"🎯 Target URL: {result['request']['url']}")
            print(f"📤 Method: {result['request']['method']}")
            print(f"📥 Status Code: {result['response']['status_code']}")
            
            if result['response']['status_code'] == 200:
                print("✅ Request completed successfully")
            else:
                print(f"⚠️  Request completed with status {result['response']['status_code']}")
            
            print("\n📋 Response body:")
            print(json.dumps(result['response']['body'], indent=2, ensure_ascii=False))
            
        else:
            print(f"❌ Replay failed!")
            print(f"📁 File: {result.get('file_path', args.file)}")
            print(f"🚨 Error: {result['error']}")
            print(f"📝 Details: {result['details']}")
            
            if 'replay_info' in result:
                print(f"⏰ Original timestamp: {result['replay_info']['original_timestamp']}")
                print(f"🔄 Replay timestamp: {result['replay_info']['replay_timestamp']}")

async def run_test_proxy(args):
    """Test proxy connectivity and authentication"""
    print("🔍 Testing proxy connectivity...")
    print(f"Proxy URL: {args.proxy_url}")
    
    # Parse authentication if provided
    proxy_auth = None
    if args.proxy_auth:
        try:
            proxy_auth = parse_proxy_auth(args.proxy_auth)
            print(f"Authentication: enabled (user: {proxy_auth[0]})")
        except ValueError as e:
            print(f"❌ Error parsing proxy authentication: {e}")
            return
    else:
        print("Authentication: none")
    
    print("-" * 50)
    print("🚀 Starting proxy test...")
    
    # Test the proxy connection
    result = await test_proxy_connection(args.proxy_url, proxy_auth)
    
    print("-" * 50)
    
    if result["success"]:
        print("✅ Proxy test SUCCESSFUL!")
        print(f"   Response time: {result['response_time']}ms")
        print(f"   Status code: {result['status_code']}")
        if "origin_ip" in result:
            print(f"   Origin IP: {result['origin_ip']}")
        print("\n🎉 Your proxy configuration is working correctly!")
        print("   You can now use these settings with the server:")
        if proxy_auth:
            print(f"   python proxy.py server --proxy-url {args.proxy_url} --proxy-auth {proxy_auth[0]}:****")
        else:
            print(f"   python proxy.py server --proxy-url {args.proxy_url}")
    else:
        print("❌ Proxy test FAILED!")
        print(f"   Error: {result['error']}")
        
        if "407" in str(result['error']) or "Authentication Required" in str(result['error']):
            print("\n💡 Troubleshooting tips for 407 Authentication Required:")
            print("   1. Double-check your username and password")
            print("   2. Try URL-encoding special characters in credentials")
            print("   3. For domain authentication, try: DOMAIN\\username or username@domain.com")
            print("   4. Contact your IT department to verify proxy settings")
        elif "timeout" in str(result['error']).lower():
            print("\n💡 Troubleshooting tips for timeout:")
            print("   1. Check if the proxy URL and port are correct")
            print("   2. Verify network connectivity to the proxy server")
            print("   3. Try a different proxy port (common: 8080, 3128, 8888)")
        else:
            print("\n💡 General troubleshooting:")
            print("   1. Verify the proxy URL format: http://proxy.company.com:port")
            print("   2. Check if the proxy requires authentication")
            print("   3. Test with a web browser using the same proxy settings")
        
        print(f"\n📖 For more help, see: PROXY_TROUBLESHOOTING.md")

def main():
    """Main function to handle server, replay, and test-proxy modes"""
    args = parse_arguments()
    
    # Handle --logs-dir option
    if args.logs_dir:
        print(f"Log files are saved in: {LOG_DIR}")
        return
    
    if args.mode == 'server':
        # Server mode - run directly without asyncio.run()
        run_server(args)
        
    elif args.mode == 'replay':
        # Replay mode - use asyncio.run() for async operations
        asyncio.run(run_replay(args))
        
    elif args.mode == 'test-proxy':
        # Test proxy mode - use asyncio.run() for async operations
        asyncio.run(run_test_proxy(args))

if __name__ == "__main__":
    main()
