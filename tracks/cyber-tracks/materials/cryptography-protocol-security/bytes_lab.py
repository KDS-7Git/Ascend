"""Encoding and integrity experiments using synthetic bytes."""
import base64
import hashlib
import hmac
message = b"note=training;amount=10"
key = b"public-training-key-not-for-real-use"
if __name__ == "__main__":
    print("hex",message.hex())
    print("base64",base64.b64encode(message).decode())
    print("sha256",hashlib.sha256(message).hexdigest())
    print("hmac",hmac.new(key,message,hashlib.sha256).hexdigest())
