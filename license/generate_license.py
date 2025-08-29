# generate_license.py===License Generator (Vendor Side)==This is for generating a license JSON for a school before selling. Put this in a file called license_tool.py on your PC only.This generates a signed license.json.Each school gets their own unique license.


Step 2: Generate License Files for Each School

Every time you sell to a new school, you create a new license.json + license.sig.

Example script:

# generate_license.py
import json, datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Load private key
with open("private.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

def create_license(school_name, allowed_machines, days_valid=365):
    license_data = {
        "school": school_name,
        "max_machines": allowed_machines,
        "issued": datetime.date.today().isoformat(),
        "expiry": (datetime.date.today() + datetime.timedelta(days=days_valid)).isoformat()
    }

    # Save license.json
    with open("license.json", "w") as f:
        json.dump(license_data, f, indent=2)

    # Sign license
    license_bytes = json.dumps(license_data, sort_keys=True).encode("utf-8")
    signature = private_key.sign(
        license_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    with open("license.sig", "wb") as f:
        f.write(signature)

    print(f"✅ License generated for {school_name}")

# Example: create license for Masala Secondary
create_license("Masaka Secondary School", allowed_machines=10, days_valid=365)


This produces:

license.json → readable license data

license.sig → cryptographic signature

You send both files to the school.