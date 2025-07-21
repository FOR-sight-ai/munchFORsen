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

async def replay_request_from_file(filepath: str, target_url: str = None, flatten_content: bool = False, no_tool_roles: bool = False, merge_headers: dict = None):
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
        
        # Perform the request
        start_time = datetime.utcnow()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TARGET_URL, json=body_to_send, headers=filtered_headers)

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
    
    # If no arguments provided, default to server mode
    if len(sys.argv) == 1:
        sys.argv.append('server')
    
    return parser.parse_args()

def run_server(args):
    """Run the proxy server"""
    global TARGET_URL, FLATTEN_CONTENT, NO_TOOL_ROLES, ENABLE_LOGGING, MERGE_HEADERS
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
    
    print(f"Starting proxy server...")
    print(f"Target URL: {TARGET_URL}")
    print(f"Content flattening: {'enabled' if FLATTEN_CONTENT else 'disabled'}")
    print(f"Tool role replacement: {'enabled' if NO_TOOL_ROLES else 'disabled'}")
    print(f"Request logging: {'enabled' if ENABLE_LOGGING else 'disabled'}")
    print(f"Header merging: {'enabled' if MERGE_HEADERS else 'disabled'}")
    print(f"Server will be available at: http://{args.host}:{args.port}")
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)

async def run_replay(args):
    """Run replay mode"""
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
    
    print("-" * 50)
    
    result = await replay_request_from_file(args.file, args.target_url, args.flatten_content, args.no_tool_roles, merge_headers)
    
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

def main():
    """Main function to handle both server and replay modes"""
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

if __name__ == "__main__":
    main()
