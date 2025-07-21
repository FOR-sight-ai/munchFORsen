# Content Flattening Feature

## Overview
Added a new `--flatten-content` option that converts message content from array format to string format when the array contains only a single text element.

## Implementation Details

### New Function: `flatten_content_in_body(body: dict) -> dict`
- Located in `proxy.py` after the `get_logs_directory()` function
- Performs deep copy to avoid modifying original request
- Only flattens content arrays with exactly one element of type "text"
- Preserves all other content structures unchanged

### Command Line Options
- Added `--flatten-content` flag to both `server` and `replay` modes
- Server mode: Applies flattening to all incoming requests before forwarding
- Replay mode: Applies flattening to replayed requests when flag is used

### Global State Management
- Added `FLATTEN_CONTENT` global variable to track server-wide setting
- Updated in `run_server()` function based on command line argument

### Modified Functions
1. **`proxy()` endpoint**: Now applies flattening before forwarding requests
2. **`replay_request_from_file()`**: Added optional `flatten_content` parameter
3. **`run_server()`**: Sets global flag and displays status
4. **`run_replay()`**: Passes flag to replay function
5. **`parse_arguments()`**: Added new argument to both parsers

## Usage Examples

### Server Mode
```bash
# Enable content flattening
python proxy.py server --flatten-content

# With other options
python proxy.py server --port 9000 --flatten-content --target-url https://api.openai.com/v1/chat/completions
```

### Replay Mode
```bash
# Replay with content flattening
python proxy.py replay log_file.json --flatten-content

# Combined with other options
python proxy.py replay log_file.json --flatten-content --target-url https://test-api.com --output json
```

## Transformation Example

**Input:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "you are an helpful assistant"
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "write a poem"
        }
      ]
    }
  ],
  "model": "mistral",
  "stop": ["<end_code>"]
}
```

**Output:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "you are an helpful assistant"
    },
    {
      "role": "user",
      "content": "write a poem"
    }
  ],
  "model": "mistral",
  "stop": ["<end_code>"]
}
```

## Edge Cases Handled
- Multi-element content arrays: Not flattened
- Non-text content types: Not flattened
- Already flattened content: Unchanged
- Missing text field: Not flattened
- Empty content arrays: Not flattened
- Invalid/missing messages: Handled gracefully

## Testing
- Comprehensive test coverage for all edge cases
- Integration testing for end-to-end functionality
- Command line interface testing
- Server startup verification

## Documentation Updates
- Updated README.md with feature description and examples
- Added help text to command line arguments
- Updated usage examples in argument parser