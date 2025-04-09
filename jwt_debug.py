#!/usr/bin/env python
"""
JWT Token Debugging Utility for ChessMate API.
This script helps analyze and debug JWT token issues.
"""

import sys
import json
import base64
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jwt_debug")

# Also print to console
def print_info(message):
    """Print message to console and log it."""
    print(message)
    logger.info(message)

def print_error(message):
    """Print error message to console and log it."""
    print(f"ERROR: {message}", file=sys.stderr)
    logger.error(message)


def base64url_decode(input):
    """Decode base64url-encoded string with proper padding handling."""
    if isinstance(input, str):
        input = input.encode("ascii")
    
    # Add padding if needed
    rem = len(input) % 4
    if rem > 0:
        input += b"=" * (4 - rem)
    
    # Replace URL-safe characters
    input = input.replace(b"-", b"+").replace(b"_", b"/")
    
    # Decode
    return base64.b64decode(input)


def decode_token_parts(token):
    """Decode the header and payload of a JWT token."""
    if not token:
        print_error("No token provided")
        return None, None
    
    try:
        # Split the token into its three parts
        parts = token.split('.')
        if len(parts) != 3:
            print_error(f"Invalid token format. Expected 3 parts, got {len(parts)}")
            return None, None
        
        # Decode the header (first part)
        header_bytes = base64url_decode(parts[0])
        header = json.loads(header_bytes)
        
        # Decode the payload (second part)
        payload_bytes = base64url_decode(parts[1])
        payload = json.loads(payload_bytes)
        
        return header, payload
    
    except Exception as e:
        print_error(f"Error decoding token: {str(e)}")
        return None, None


def analyze_token(token):
    """Analyze a JWT token and provide detailed information."""
    print_info("Analyzing JWT token...")
    
    header, payload = decode_token_parts(token)
    if not header or not payload:
        return False
    
    # Print header information
    print("\n===== TOKEN HEADER =====")
    print(json.dumps(header, indent=2))
    
    # Print payload information
    print("\n===== TOKEN PAYLOAD =====")
    print(json.dumps(payload, indent=2))
    
    # Check token expiration
    if "exp" in payload:
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.now()
        
        print("\n===== TOKEN EXPIRATION =====")
        print(f"Expiration timestamp: {exp_timestamp}")
        print(f"Expiration date/time: {exp_datetime}")
        
        if exp_datetime > now:
            time_left = exp_datetime - now
            print(f"Token is VALID (expires in {time_left})")
        else:
            time_passed = now - exp_datetime
            print(f"Token is EXPIRED (expired {time_passed} ago)")
    
    # Check for user information
    if "user_id" in payload:
        print(f"\nUser ID: {payload['user_id']}")
    
    return True


def base64url_encode(data):
    """Encode data to base64url format without padding."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    
    # Standard base64 encoding
    encoded = base64.b64encode(data).decode("ascii")
    
    # Convert to base64url
    encoded = encoded.replace("+", "-").replace("/", "_").rstrip("=")
    
    return encoded


def create_test_token(user_id=1, username="test_user", expiry_days=1):
    """Create a simple test token for debugging purposes."""
    import time
    import hmac
    import hashlib
    
    # Create a header
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    
    # Create a payload
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": now + (expiry_days * 24 * 60 * 60),
        "iat": now,
    }
    
    # Convert header and payload to base64url
    header_b64 = base64url_encode(json.dumps(header))
    payload_b64 = base64url_encode(json.dumps(payload))
    
    # Create signature (simplified, not for production use)
    secret = "debugsecretkey"
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)
    
    # Combine to form the token
    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    
    print(f"\nCreated test token: {token}")
    return token


def extract_authorization_token(auth_header):
    """Extract the token from an Authorization header."""
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() in ("bearer", "token"):
        return parts[1]
    elif len(parts) == 1:
        # Assume the header contains only the token
        return parts[0]
    
    return None


def main():
    """Run the JWT token debugging utility."""
    parser = argparse.ArgumentParser(description="Debug JWT tokens for ChessMate API")
    parser.add_argument("--token", help="JWT token to analyze")
    parser.add_argument("--auth-header", help="Authorization header containing the token")
    parser.add_argument("--create-test", action="store_true", help="Create a test token")
    parser.add_argument("--user-id", type=int, default=1, help="User ID for test token")
    parser.add_argument("--username", default="test_user", help="Username for test token")
    parser.add_argument("--expiry", type=int, default=1, help="Expiry in days for test token")
    
    args = parser.parse_args()
    
    if args.create_test:
        token = create_test_token(args.user_id, args.username, args.expiry)
        analyze_token(token)
        return
    
    token = None
    if args.token:
        token = args.token
    elif args.auth_header:
        token = extract_authorization_token(args.auth_header)
    
    if not token:
        print_error("No token provided. Use --token or --auth-header.")
        parser.print_help()
        return
    
    analyze_token(token)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {str(e)}")
        sys.exit(1) 