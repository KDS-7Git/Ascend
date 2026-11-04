# Rotate a secret and verify an artifact

Revoke a write credential and distinguish artifact integrity from signer trust.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+; OpenSSL for the local signature exercise; only synthetic credentials.

Download /training/devops-reliability-orchestration.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-reliability-orchestration folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/secret-and-artifact.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

Credentials grant authority and must be revocable; artifact digests detect content changes but do not establish who signed them. Store secrets outside release artifacts and restrict their local permissions.

## Guided practice

### Step 1

Create a synthetic token file and start a fresh service using it. Run an authenticated write check, then attempt the same write without credentials.

### Step 2

```sh
mkdir -p secrets work notes
printf '%s\n' 'synthetic-old-token' > secrets/write-token.txt
chmod 600 secrets/write-token.txt
python3 shared/relay.py --data work/secret.sqlite --release secret-v1 --token-file secrets/write-token.txt
```

### Step 3

```sh
python3 shared/check_service.py --expect-release secret-v1 --write --token-file secrets/write-token.txt
python3 shared/check_service.py --expect-release secret-v1 --write
```

### Step 4

Save a separate old-client token file, replace the server token file with a new synthetic value, and show that the old client fails while the new client succeeds. Never paste actual tokens into the notebook.

### Step 5

Build a source artifact and use a temporary local signing key to sign its manifest. Keep the signature outside the immutable artifact directory.

### Step 6

```sh
python3 shared/release.py build --source shared/relay.py --out work/signed-artifact --release signed-v1 --revision local-reviewed
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out secrets/signing.pem
openssl pkey -in secrets/signing.pem -pubout -out notes/signer-public.pem
openssl dgst -sha256 -sign secrets/signing.pem -out notes/manifest.sig work/signed-artifact/manifest.json
openssl dgst -sha256 -verify notes/signer-public.pem -signature notes/manifest.sig work/signed-artifact/manifest.json
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change a copied manifest and verify the signature rejection. Verify that an untrusted replacement public key cannot establish the intended signer merely because it verifies some signature.

2. Rotate the synthetic write token without restarting the application, then prove revoked/new client behaviour.

3. Explain where a real CI workload identity or signature provenance policy would add assurance beyond this local self-controlled key.

## Finish line

Old credentials are denied, current legitimate writes work, and altered content fails signature/digest controls with accurately scoped signer trust. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
