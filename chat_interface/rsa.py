import json
import hashlib
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

def sign_json_rsa(data):
    """
    Sign JSON data with RSA private key
    """
    # Convert to string with sorted keys
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    
    # Hash the data
    data_hash = hashlib.sha256(json_str.encode('utf-8')).digest()
    
    # Generate keys (do this once and share public key)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Sign with private key
    signature = private_key.sign(
        data_hash,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    # Base64 encode
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Add signature to data
    signed_data = data.copy()
    signed_data['signature'] = signature_b64
    signed_data['public_key'] = private_key
    return signed_data

def verify_json_rsa(signed_data):
    """
    Verify RSA signature of JSON data
    """
    # Extract signature
    received_signature = signed_data.pop('signature', None)
    if not received_signature:
        return False, "No signature found"
    
    received_public_key = signed_data.pop('public_key', None)
    if not received_public_key:
        return False, "No public key found"
    
    # Recreate the signed string
    json_str = json.dumps(signed_data, sort_keys=True, separators=(',', ':'))
    
    # Hash the data
    data_hash = hashlib.sha256(json_str.encode('utf-8')).digest()
    
    # Decode signature
    try:
        signature_bytes = base64.b64decode(received_signature)
        
        # Verify signature
        received_public_key.verify(
            signature_bytes,
            data_hash,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True, "Signature verified"
    
    except Exception as e:
        return False, f"Signature verification failed: {str(e)}"


# Example usage
data = {"message": "Hello, World!", "id": 123}
signed_data = sign_json_rsa(data)
print("Signed Data:", signed_data, "\n")
is_valid, message = verify_json_rsa(signed_data)
print("Verification:", is_valid, message)
print("Original Data:", signed_data)