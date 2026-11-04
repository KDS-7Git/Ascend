"""Evaluate a release rule using supplied observations, without CI credentials.

This local exercise does not authenticate the fixture or turn its trusted flag
into a real identity assertion. Actual CI/provider observations are separate.
"""

import argparse
import json
from pathlib import Path


def evaluate(document, expected_revision, candidate=None, artifact=None):
    if not isinstance(document, dict) or not isinstance(document.get("commits"), list):
        raise TypeError("Expected a document with commit observations")
    commits = document["commits"]
    if not commits or any(
        not isinstance(row, dict) or not isinstance(row.get("id"), str)
        for row in commits
    ):
        raise ValueError("Each commit observation needs an ID")
    if len({row["id"] for row in commits}) != len(commits):
        raise ValueError("Ambiguous duplicate commit observations")
    if (candidate is None) != (artifact is None):
        raise ValueError("Provide candidate and artifact together")
    selected = (
        document.get("selected")
        if candidate is None
        else {"commit": candidate, "artifact": artifact}
    )
    if (
        not isinstance(selected, dict)
        or not isinstance(selected.get("commit"), str)
        or not isinstance(selected.get("artifact"), str)
    ):
        raise TypeError("Selected candidate needs a commit and artifact identity")
    reasons = []
    if selected["commit"] != expected_revision:
        reasons.append("candidate is not the expected revision")
    matches = [row for row in commits if row["id"] == selected["commit"]]
    if not matches:
        reasons.append("candidate has no supplied test/identity observation")
    else:
        observed = matches[0]
        if observed.get("tests") != "passed":
            reasons.append("tests did not pass for this candidate")
        if observed.get("trusted") is not True:
            reasons.append("the supplied trust condition is not satisfied")
        if not observed.get("artifact") or selected["artifact"] != observed["artifact"]:
            reasons.append("artifact differs from the observed candidate artifact")
    return {
        "candidate": selected,
        "expected_revision": expected_revision,
        "allowed_by_rule": not reasons,
        "denial_reasons": reasons,
        "authority": "learner-local evaluation of supplied facts",
        "satisfies_track_evidence": False,
        "scope": "No CI/API credentials, signatures or provider trust were checked. The fixture's synthetic artifact labels are not verified image digests.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture")
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--artifact")
    args = parser.parse_args()
    try:
        result = evaluate(
            json.loads(Path(args.fixture).read_text()),
            args.expected_revision,
            args.candidate,
            args.artifact,
        )
    except (OSError, TypeError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["allowed_by_rule"] else 1)


if __name__ == "__main__":
    main()
