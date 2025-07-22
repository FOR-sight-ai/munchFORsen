# Corporate Proxy Troubleshooting Guide

## 407 Authentication Required Error

If you're getting a "407 Authentication Required" error, this means your corporate proxy is rejecting the authentication credentials. Here are the most common causes and solutions:

### 1. Check Your Credentials Format

Make sure your credentials are in the correct format:
```bash
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password
```

**Important**: If your username or password contains special characters (like `@`, `:`, `%`, etc.), you may need to URL-encode them:
- `@` becomes `%40`
- `:` becomes `%3A`
- `%` becomes `%25`
- Space becomes `%20`

Example:
```bash
# If your username is "user@domain" and password is "pass:word"
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth "user%40domain:pass%3Aword"
```

### 2. Enable Debug Mode

Use the `--proxy-debug` flag to get more detailed error information:
```bash
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password --proxy-debug
```

### 3. Test Different Authentication Methods

#### Basic Authentication (Default)
```bash
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password
```

#### Domain Authentication
If your corporate network uses domain authentication, try including the domain:
```bash
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth "DOMAIN\\username:password"
# or
python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth "username@domain.com:password"
```

### 4. Check Proxy URL Format

Make sure your proxy URL is correct:
```bash
# HTTP proxy
python proxy.py server --proxy-url http://proxy.company.com:8080

# HTTPS proxy
python proxy.py server --proxy-url https://proxy.company.com:8080

# With port explicitly specified
python proxy.py server --proxy-url http://proxy.company.com:3128
```

### 5. Test Proxy Connectivity

Before using the proxy with the application, test if you can connect to it:

#### Using curl (if available):
```bash
# Test basic connectivity
curl -x http://proxy.company.com:8080 http://httpbin.org/ip

# Test with authentication
curl -x http://username:password@proxy.company.com:8080 http://httpbin.org/ip
```

#### Using Python script:
```python
import httpx

# Test proxy connection
try:
    with httpx.Client(proxy="http://username:password@proxy.company.com:8080") as client:
        response = client.get("http://httpbin.org/ip")
        print("Proxy test successful:", response.json())
except Exception as e:
    print("Proxy test failed:", e)
```

### 6. Common Corporate Proxy Issues

#### NTLM Authentication
Some corporate proxies use NTLM authentication, which is not directly supported by httpx. In this case, you may need to:
1. Use a local proxy tool like `px` or `cntlm` that handles NTLM authentication
2. Configure the application to use the local proxy instead

#### Certificate Issues
If using HTTPS proxy, you might encounter certificate issues:
```bash
# For testing only - disable SSL verification (NOT recommended for production)
export PYTHONHTTPSVERIFY=0
```

#### Firewall/Network Restrictions
- Ensure the proxy server allows connections to your target URLs
- Check if there are any IP restrictions
- Verify that the required ports are open

### 7. Environment Variables

You can also set proxy configuration via environment variables:
```bash
export HTTP_PROXY=http://username:password@proxy.company.com:8080
export HTTPS_PROXY=http://username:password@proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.local

python proxy.py server
```

### 8. Debugging Steps

1. **Verify credentials**: Double-check username and password with your IT department
2. **Test with browser**: Configure your browser to use the same proxy settings
3. **Check proxy logs**: Ask your IT department to check proxy server logs for authentication failures
4. **Try different ports**: Some proxies listen on multiple ports (8080, 3128, 8888)
5. **Test from different network**: Try from a different network location if possible

### 9. Alternative Solutions

If direct proxy authentication doesn't work:

#### Option 1: Use a local proxy tunnel
```bash
# Install and configure a local proxy tool like 'px'
pip install px-proxy
px --proxy=proxy.company.com:8080 --username=yourusername --password=yourpassword --port=3128

# Then use the local proxy
python proxy.py server --proxy-url http://localhost:3128
```

#### Option 2: Use SSH tunnel (if SSH access is available)
```bash
# Create SSH tunnel
ssh -D 1080 user@jumphost.company.com

# Use SOCKS proxy
python proxy.py server --proxy-url socks5://localhost:1080
```

### 10. Getting Help

If none of these solutions work:

1. **Contact IT Support**: Provide them with:
   - The exact error message
   - Proxy server address and port
   - Your username (not password)
   - The application you're trying to use

2. **Collect Debug Information**:
   ```bash
   python proxy.py server --proxy-url http://proxy.company.com:8080 --proxy-auth username:password --proxy-debug > debug.log 2>&1
   ```

3. **Test with minimal example**:
   ```python
   import httpx
   
   proxy_url = "http://username:password@proxy.company.com:8080"
   
   try:
       with httpx.Client(proxy=proxy_url) as client:
           response = client.get("https://httpbin.org/ip", timeout=10)
           print("Success:", response.status_code, response.json())
   except httpx.ProxyError as e:
       print("Proxy Error:", e)
   except Exception as e:
       print("Other Error:", e)
   ```

## Security Notes

- Never commit proxy credentials to version control
- Use environment variables or secure credential storage for production
- Consider using service accounts for automated systems
- Regularly rotate proxy credentials as per company policy