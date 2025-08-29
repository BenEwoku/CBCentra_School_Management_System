#Step 3: App-Side License Verification + Device Binding. This is for the desktop app. Put this in a file called app_license.py inside your app folder.

import json
import base64
import uuid
import pathlib
import hmac, hashlib
from datetime import date
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ------------------------------
# Embed your public key here
# ------------------------------
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
YOUR_PUBLIC_KEY_HERE
-----END PUBLIC KEY-----"""

# Salt for HMAC to protect activations file
ACTIVATION_HMAC_SALT = b"change_this_random_salt_32_bytes_min"

def get_machine_id():
    """Returns a stable machine identifier"""
    mac = uuid.getnode()
    return f"MAC-{mac:012X}"

def _hmac_digest(data: bytes) -> str:
    return hmac.new(ACTIVATION_HMAC_SALT, data, hashlib.sha256).hexdigest()

def _read_activations(activation_path, school):
    p = pathlib.Path(activation_path)
    if not p.exists():
        return {"school": school, "devices": [], "hmac": ""}
    data = json.loads(p.read_text())
    stored_hmac = data.get("hmac", "")
    data_copy = {"school": data.get("school",""), "devices": data.get("devices", [])}
    if _hmac_digest(json.dumps(data_copy,separators=(",",":")).encode()) != stored_hmac:
        raise ValueError("Activation file tampered!")
    if data_copy["school"] != school:
        raise ValueError("Activation file belongs to a different school!")
    return data

def _write_activations(activation_path, school, devices):
    data_copy = {"school": school, "devices": devices}
    raw = json.dumps(data_copy, separators=(",",":")).encode()
    h = _hmac_digest(raw)
    to_write = {"school": school, "devices": devices, "hmac": h}
    pathlib.Path(activation_path).write_text(json.dumps(to_write, indent=2))

def ensure_license_ok(license_path, activation_path="activations.json"):
    """
    Verify license and register this machine (up to max_devices)
    Returns (True, message) or (False, error)
    """
    try:
        license_obj = json.load(open(license_path))
        payload_b = base64.b64decode(license_obj["payload"])
        signature_b = base64.b64decode(license_obj["signature"])
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)

        # Verify signature
        public_key.verify(
            signature_b,
            payload_b,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

        license_data = json.loads(payload_b)
    except Exception as e:
        return False, f"Invalid or tampered license: {e}"

    # Expiry check
    expiry = date.fromisoformat(license_data["expiry"])
    if date.today() > expiry:
        return False, f"License expired on {expiry}"

    # Activation / device binding
    try:
        act = _read_activations(activation_path, license_data["school"])
    except Exception as e:
        act = {"school": license_data["school"], "devices": [], "hmac": ""}

    devices = set(act.get("devices", []))
    machine_id = get_machine_id()

    if machine_id in devices:
        return True, f"✅ Machine already activated for {license_data['school']}."

    if len(devices) >= int(license_data["max_devices"]):
        return False, f"License device limit reached for {license_data['school']}"

    # Register this machine
    devices.add(machine_id)
    _write_activations(activation_path, license_data["school"], sorted(devices))
    return True, f"✅ Activated this machine for {license_data['school']} ({len(devices)}/{license_data['max_devices']})"
