import base64
import json
import sys

def decode_jwt_payload(token):
    """Decode JWT payload without verification"""
    try:
        # Split the token into parts
        parts = token.split('.')
        if len(parts) != 3:
            return "Invalid token format"
        
        # Decode the payload (second part)
        payload = parts[1]
        
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # Parse JSON
        payload_data = json.loads(decoded_str)
        
        return json.dumps(payload_data, indent=2)
    except Exception as e:
        return f"Error decoding token: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_jwt.py <jwt_token>")
        sys.exit(1)
    
    token = sys.argv[1]
    print("JWT Payload:")
    print(decode_jwt_payload(token))