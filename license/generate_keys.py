🏫 School Licensing Workflow
🔑 Step 1: Generate Your Private + Public Keys (one-time setup)

You (the vendor) create one private key and one public key.

Private key (PEM) → only you keep it safe!

Public key (PEM) → you embed inside your desktop app (read-only).

Run this once on your machine:

# generate_keys.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# Save private key (KEEP SECRET!)
with open("private.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Save public key (embed in app)
with open("public.pem", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

print("✅ Keys generated: private.pem, public.pem")


👉 You only do this once.
Keep private.pem very secure — if leaked, anyone can forge licenses.
Put public.pem into your app folder.