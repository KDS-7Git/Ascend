# Separate build identity from deployment authority

Require both a passing change and the intended identity before a release is eligible.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

A local copy of the supplied workflow and fixture; owned CI/cloud accounts only for the optional real identity extension.

Download /training/devops-delivery-automation.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-delivery-automation folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/pipeline-trust.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

An untrusted pull request executes code. Repository permissions, secret release conditions and OIDC trust policies decide what that code can access. A green test is not permission to deploy.

## Guided practice

### Step 1

Inspect the workflow's events and permissions. Identify why the test job does not need a deployment credential or write access to repository content.

### Step 2

```sh
cat configs/workflow.yml
cat fixtures/pipeline.json
```

### Step 3

Execute the readable local policy gate against the authored fixture. The initial selection points to a failed change; an explicitly selected passing/trusted change should be allowed. This evaluates supplied facts and does not authenticate a real CI identity.
```sh
python3 tools/pipeline_policy.py fixtures/pipeline.json --expected-revision commit-a
python3 tools/pipeline_policy.py fixtures/pipeline.json --expected-revision commit-a --candidate commit-a --artifact sha256:aaa
python3 tools/pipeline_policy.py fixtures/pipeline.json --expected-revision commit-c --candidate commit-c --artifact sha256:ccc
```

### Step 4

Construct a release decision table using fixture commit-a, commit-b and commit-c. A candidate must satisfy the expected revision/artifact, passing tests and the intended trust boundary.

### Step 5

In your owned repository, observe a fork/untrusted-change workflow without adding deployment secrets; record its event, permissions and run revision. Provider OIDC is an extension: use that provider's real policy tools to test issuer, audience, repository/ref/environment and token lifetime. A provider-free policy experiment proves only the local decision rule.

### Step 6

Pin reviewed action commit SHAs and retain their upstream release references before treating the workflow as a production policy. The provided tagged action versions are a readable starter.

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Change one claim or trust condition in a copied policy/fixture and show why the candidate becomes ineligible even though tests passed.

2. For a real OIDC variant, retain the denied/allowed provider observations without exposing tokens. With no provider, explicitly retain policy analysis as analysis only.

3. Explain why echoing a secret, giving pull requests broad write permissions or using a shared privileged runner would break the boundary.

## Finish line

The learner distinguishes test success from deployment authority and demonstrates or accurately scopes both an allowed and a denied identity path. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
