pip install cryptography  #===this is needed for signing/verifying keys


This is for generating the keys you’ll use to sign licenses. Do it once on your computer (vendor side).

Open terminal or command prompt.

Run:

# Generate private key (keep secret!)
openssl genrsa -out private.pem 2048

# Generate public key (for bundling in app)
openssl rsa -in private.pem -pubout -out public.pem


private.pem → only you keep, used for signing licenses.

public.pem → bundle in your app, used for verification.

