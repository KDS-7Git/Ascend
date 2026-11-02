"""Constrained browser fixtures and private, deterministic evidence rubrics."""

from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import secrets

from ascend.labs import access_decision, generate as native_generate


EXAMPLES = {
    "access": (
        "Disabled identities are denied first. Enabled owners can read and write. An enabled admin can read another owner’s file, but cannot write it.",
        {
            "caller": "Mira",
            "owner": "Dev",
            "enabled": True,
            "role": "admin",
            "action": "write",
        },
        "Mira is enabled but is not the owner. The admin exception permits read only, so this write is denied. Change only action to read: it is allowed. Disable Mira: even the read is denied. Test one condition at a time.",
        "request-decisions",
    ),
    "subnet": (
        "An IPv4 prefix fixes the network bits. For an ordinary /26 subnet, 6 bits remain: 64 addresses, of which 62 are usable hosts.",
        {"interface": "192.0.2.70/26", "block_starts": [0, 64, 128, 192]},
        "70 lies in the block 64–127. The network is 192.0.2.64/26; broadcast is 192.0.2.127; hosts are .65–.126. A /27 instead has 32 addresses and 30 usable hosts. Compare the requested host count to usable capacity, not the final octet.",
        "address-boundaries",
    ),
    "logging": (
        "Use a request marker to select related events. A 2xx status means success; a status of 400 or higher means failure in this exercise. Counts from other markers do not describe your request.",
        [
            {"id": "e1", "marker": "blue", "status": 200},
            {"id": "e2", "marker": "blue", "status": 503},
            {"id": "e3", "marker": "amber", "status": 404},
        ],
        "Filter marker=blue: e1 and e2 remain. Only e2 failed, so the count is one. Filtering status=200 would hide the failure; an empty error panel alone does not prove the service is healthy. Preserve the full stream as your comparison.",
        "event-filter",
    ),
    "integrity": (
        "A SHA-256 digest describes exact bytes. Compare a copy against a separately trusted digest. A matching digest supports byte equality, not claims about who created the file.",
        {"trusted_content": "note\n", "copy_A": "note\n", "copy_B": "note"},
        "A matches; B lost the final newline and has a different digest. Renaming A does not change its bytes. A matching digest cannot establish a chain of custody unless the reference itself is trusted. Use the digest calculator in the next exercise to compare exact UTF-8 text.",
        "copy-check",
    ),
    "timeline": (
        "Normalize timestamps and sort events before proposing a sequence. Repeated failures followed by success are an investigation lead, not proof of an attacker.",
        [
            {"id": "a", "time": "09:00:20", "status": "success"},
            {"id": "b", "time": "09:00:00", "status": "failure"},
            {"id": "c", "time": "09:00:10", "status": "failure"},
        ],
        "The order is b,c,a. Two failures precede success within 20 seconds. A user correcting a password is also consistent with this pattern. If success were before the failures, the proposed failure-then-success sequence would no longer hold. Ask for independent evidence before attributing intent.",
        "event-order",
    ),
}


def field(label, type="text", options=None):
    return dict(
        label=label, type=type, **({"options": options} if options is not None else {})
    )


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def result(
    instructions, data, expected, fields, debrief, *, transfer=False, followup=None
):
    return dict(
        public=dict(instructions=instructions, data=data, fields=fields),
        expected=expected,
        debrief=debrief,
        transfer=transfer,
        followup=followup,
    )


def policy_fixture(count=6):
    fixture = native_generate("access-policy", None, None)
    requests = fixture["public"]["data"]["requests"]
    # Preserve native access semantics; scale an audit with contrasting controls.
    while len(requests) < count:
        request = deepcopy(secrets.choice(requests))
        request.update(
            id=f"r{len(requests) + 1}",
            enabled=secrets.choice([True, False]),
            action=secrets.choice(["read", "write"]),
        )
        requests.append(request)
    return requests


def workspace_fixture(family):
    if family == "access":
        return {
            "policy": {
                "deny_disabled": True,
                "owner_access": True,
                "admin_read": True,
                "admin_write": False,
            },
            "requests": [
                {
                    "id": "owner-control",
                    "caller": "Ari",
                    "owner": "Ari",
                    "enabled": True,
                    "role": "user",
                    "action": "write",
                },
                {
                    "id": "reader",
                    "caller": "Bo",
                    "owner": "Ari",
                    "enabled": True,
                    "role": "admin",
                    "action": "read",
                },
                {
                    "id": "writer",
                    "caller": "Bo",
                    "owner": "Ari",
                    "enabled": True,
                    "role": "admin",
                    "action": "write",
                },
                {
                    "id": "disabled-control",
                    "caller": "Ari",
                    "owner": "Ari",
                    "enabled": False,
                    "role": "user",
                    "action": "read",
                },
            ],
        }
    return {
        "marker": "",
        "minimum_status": 0,
        "events": [
            {"id": "e1", "time": "09:00:10", "marker": "deploy", "status": 503},
            {"id": "e2", "time": "09:00:00", "marker": "deploy", "status": 200},
            {"id": "e3", "time": "09:00:20", "marker": "health", "status": 200},
        ],
    }


def experiment(family, work):
    if not isinstance(work, dict):
        raise ValueError("Workspace must be a JSON object")
    if family == "access":
        policy, requests = work.get("policy"), work.get("requests")
        if (
            not isinstance(policy, dict)
            or set(policy)
            != {"deny_disabled", "owner_access", "admin_read", "admin_write"}
            or any(type(v) is not bool for v in policy.values())
        ):
            raise ValueError(
                "Policy needs four boolean rules: deny_disabled, owner_access, admin_read, admin_write"
            )
        if not isinstance(requests, list) or len(requests) > 100:
            raise ValueError("Use at most 100 requests")
        rows = []
        for r in requests:
            if (
                not isinstance(r, dict)
                or not {"id", "caller", "owner", "enabled", "role", "action"}
                <= r.keys()
                or type(r["enabled"]) is not bool
                or not all(
                    isinstance(r[k], str)
                    for k in ("id", "caller", "owner", "role", "action")
                )
                or r["role"] not in {"admin", "user"}
                or r["action"] not in {"read", "write"}
            ):
                raise ValueError(
                    "Each request needs id, caller, owner, enabled (boolean), role (admin/user) and action (read/write)"
                )
            allowed = not (policy["deny_disabled"] and not r["enabled"]) and (
                (policy["owner_access"] and r["caller"] == r["owner"])
                or (r["role"] == "admin" and policy["admin_" + r["action"]])
            )
            rows.append({"id": r["id"], "allowed": allowed})
        return rows
    events = work.get("events")
    if (
        not isinstance(events, list)
        or len(events) > 200
        or type(work.get("minimum_status", 0)) is not int
        or not isinstance(work.get("marker", ""), str)
    ):
        raise ValueError(
            "Use at most 200 events, a text marker and an integer minimum_status"
        )
    for e in events:
        if (
            not isinstance(e, dict)
            or not {"id", "time", "marker", "status"} <= e.keys()
            or not all(isinstance(e[k], str) for k in ("id", "time", "marker"))
            or type(e["status"]) is not int
        ):
            raise ValueError(
                "Each event needs text id, time, marker and integer status"
            )
    return sorted(
        (
            e
            for e in events
            if (not work.get("marker") or e["marker"] == work["marker"])
            and e["status"] >= work.get("minimum_status", 0)
        ),
        key=lambda e: e["time"],
    )


def mystery(item, variant):
    """Finite contrasting cases; no cosmetic seed is advertised as new content."""
    if item["id"] == "room-41":
        return delivery_mystery(item, variant)
    if item["id"] == "room-63":
        return incident_mystery(item, variant)
    logging_case = item["id"] == "desk-28"
    if logging_case:
        explanations = [
            "The dashboard filter hides errors",
            "The service failed during this window",
            "There is insufficient evidence of a failure",
        ]
        streams = [
            [
                {"id": "e1", "status": 200, "marker": "job"},
                {"id": "e2", "status": 503, "marker": "job"},
                {"id": "e3", "status": 200, "marker": "health"},
            ],
            [
                {"id": "e1", "status": 503, "marker": "job"},
                {"id": "e2", "status": 503, "marker": "job"},
                {"id": "e3", "status": 200, "marker": "health"},
            ],
            [
                {"id": "e1", "status": 200, "marker": "job"},
                {"id": "e2", "status": 200, "marker": "job"},
                {"id": "e3", "status": 404, "marker": "other"},
            ],
        ]
        data = {
            "events": streams[variant],
            "dashboard_filter": "status = 200" if variant == 0 else "marker = job",
            "scope": "Only marker job belongs to this job. All events in the window are included.",
        }
        expected = {
            "conclusion": explanations[variant],
            "evidence": "e2",
            "prediction": [2, 2, 0][variant],
        }
        fields = {
            "conclusion": field(
                "Which explanation fits this window?", "select", explanations
            ),
            "evidence": field(
                "Which final job record supports this conclusion?",
                "select",
                ["e1", "e2", "e3"],
            ),
            "prediction": field(
                "If e1 is changed to status 503, how many job failures will the unfiltered stream contain?",
                "integer",
            ),
        }
        # In the benign variant e1 changing to 503 creates one failure.
        expected["prediction"] = [2, 2, 1][variant]
        debrief = [
            "e2 failed but status=200 excluded it. A healthy health check does not cancel a job failure.",
            "Both job records failed even without a restrictive status filter. A healthy separate health check does not establish job success.",
            "Both job records succeeded; e3 belongs to a different marker. Calling this a failed job exceeds the evidence.",
        ][variant]
    else:
        causes = [
            "The identity is disabled",
            "The caller does not own the destination",
            "The reported fault is not reproduced",
        ]
        target = {
            "id": "r2",
            "caller": "Bo",
            "owner": "Ari",
            "enabled": True,
            "role": "admin",
            "action": "write",
        }
        if variant == 0:
            target.update(caller="Ari", enabled=False)
        if variant == 2:
            target.update(caller="Ari")
        requests = [
            dict(
                id="r1",
                caller="Ari",
                owner="Ari",
                enabled=True,
                role="user",
                action="write",
            ),
            target,
            dict(
                id="r3",
                caller="Bo",
                owner="Ari",
                enabled=True,
                role="admin",
                action="read",
            ),
        ]
        records = [
            {**r, "observed": "allowed" if access_decision(r)[0] else "denied"}
            for r in requests
        ]
        data = {
            "policy": "Disabled identities are denied. Enabled owners read/write. Enabled admins read others’ objects; only owners write.",
            "requests": records,
            "report": "The handover write r2 is reported as denied. Compare that report with these captured outcomes.",
        }
        expected = {
            "conclusion": causes[variant],
            "evidence": "r2",
            "prediction": variant == 2,
        }
        fields = {
            "conclusion": field("Which conclusion is supported?", "select", causes),
            "evidence": field(
                "Which captured request supports your conclusion?",
                "select",
                ["r1", "r2", "r3"],
            ),
            "prediction": field(
                "If only r2 action changes to read, will it be allowed?", "boolean"
            ),
        }
        expected["prediction"] = variant != 0
        debrief = [
            "r2 is disabled even though Ari owns the file. Changing write to read cannot bypass the disabled check. r1 proves owner writes work when enabled.",
            "r2 is an enabled admin writing someone else’s file. Admin read is allowed, but write requires ownership. r1 rules out a broken owner workflow.",
            "r2 is an enabled owner and the capture shows success. The denial report is not reproduced. Gather a matching failed request before asserting a fault.",
        ][variant]
    return result(
        item["brief"]
        + " Submit every evidence check and changed-condition prediction. Notes are for reflection and are not automatically graded.",
        data,
        expected,
        fields,
        debrief
        + " The changed-condition prediction tests whether your explanation transfers.",
        transfer=True,
        followup="event-compare" if logging_case else "request-change",
    )


def delivery_mystery(item, variant):
    """A different fixture from the mini handover: an approval/dispatch pipeline."""
    causes = [
        "The publishing credential expired",
        "The destination belongs to another team",
        "The reported delivery failure is not reproduced",
    ]
    job = {
        "id": "j7",
        "approved": True,
        "team": "blue",
        "destination_team": "blue",
        "credential_valid": True,
    }
    if variant == 0:
        job["credential_valid"] = False
    if variant == 1:
        job["destination_team"] = "green"
    data = {
        "scope": "All dispatch attempts for this window are included. A publish is allowed only when approved, the credential is valid and job team equals destination team. Reading a queue does not require publish permission.",
        "jobs": [
            job,
            {
                "id": "j8",
                "approved": True,
                "team": "green",
                "destination_team": "green",
                "credential_valid": True,
            },
            {
                "id": "j9",
                "approved": False,
                "team": "blue",
                "destination_team": "blue",
                "credential_valid": True,
            },
        ],
        "dispatch_log": [
            {
                "id": "d1",
                "request": "q1",
                "job": "j7",
                "operation": "read",
                "status": 200,
                "time": "01:10:00Z",
            },
            {
                "id": "d2",
                "request": "q2",
                "job": "j8",
                "operation": "publish",
                "status": 200,
                "time": "01:10:02Z",
            },
            {
                "id": "d3",
                "request": "q3",
                "job": "j7",
                "operation": "publish",
                "status": 200 if variant == 2 else 403,
                "time": "01:10:04Z",
            },
            {
                "id": "d4",
                "request": "q4",
                "job": "j9",
                "operation": "publish",
                "status": 403,
                "time": "01:10:06Z",
            },
        ],
        "delivery_log": [
            {"id": "a1", "request": "q2", "state": "stored", "time": "01:10:03Z"},
            {
                "id": "a2",
                "request": "q3",
                "state": "stored" if variant == 2 else "not dispatched",
                "time": "01:10:05Z",
            },
        ],
        "report": "The operator claims the j7 delivery failed because every worker is offline. A read succeeded, so a colleague suggests granting universal publish access.",
        "actions": {
            "A": "Grant universal publish access",
            "B": "Renew only the j7 credential",
            "C": "Route j7 to its blue destination",
            "D": "Keep permissions and request the exact failing attempt",
        },
        "tests": "Predict changing only credential_valid to true, then changing only destination_team to blue on the ORIGINAL j7 fixture. Keep j8 enabled and j9 unapproved as controls.",
    }
    expected = {
        "conclusion": causes[variant],
        "dispatch_evidence": "d3",
        "delivery_evidence": "a2",
        "offline_counterexample": "d2",
        "repair": ["B", "C", "D"][variant],
        "credential_only": variant != 1,
        "destination_only": variant != 0,
        "approved_control": True,
        "unapproved_control": False,
        "delivery_count": 2 if variant == 2 else 1,
    }
    fields = {
        "conclusion": field("Best supported conclusion for j7", "select", causes),
        "dispatch_evidence": field(
            "Dispatch record for the reported publish",
            "select",
            ["d1", "d2", "d3", "d4"],
        ),
        "delivery_evidence": field(
            "Delivery record joined to that same request", "select", ["a1", "a2"]
        ),
        "offline_counterexample": field(
            "Successful publish for another job that tests the all-workers-offline claim",
            "select",
            ["d1", "d2", "d3", "d4"],
        ),
        "repair": field(
            "Narrowest action supported by the evidence", "select", ["A", "B", "C", "D"]
        ),
        "credential_only": field(
            "Would renewing only the j7 credential allow its publish?", "boolean"
        ),
        "destination_only": field(
            "Would correcting only the j7 destination allow its publish?", "boolean"
        ),
        "approved_control": field(
            "Must j8 remain publishable after your action?", "boolean"
        ),
        "unapproved_control": field(
            "May j9 publish while still unapproved?", "boolean"
        ),
        "delivery_count": field(
            "Number of stored deliveries in the original window", "integer"
        ),
    }
    return result(
        item["brief"]
        + " Join the two logs by request, evaluate the original state for each prediction, and preserve both controls.",
        data,
        expected,
        fields,
        [
            "The expired j7 credential blocks publish. d3 joins to a2; d2 shows that a different publish succeeded. Renewing j7 alone preserves the approval boundary.",
            "The j7 destination is green while its team is blue. Renewing an already valid credential cannot fix the mismatch. Correct its route and preserve approval checks.",
            "d3 and a2 show j7 was published and stored. The claimed failure is not reproduced. d4 is an expected denial for an unapproved, different job.",
        ][variant]
        + " A queue read is a different operation from publish. Granting universal access would break the unapproved-job control.",
        transfer=True,
        followup="event-compare",
    )


def incident_mystery(item, variant):
    """A mixed-evidence dossier with independent subclaims and clock normalization."""
    reference = "total=17\n"
    copy = [reference, "total=71\n", "total=17\r\n"][variant]
    exported = [reference, reference, "total=17\r\n"][variant]
    data = {
        "scope": "Investigate four claims separately: an archive changed in transit, a login was malicious, an export was unauthorized, and every service was unavailable. Captures are complete for this window. No actor-attribution evidence beyond these records exists.",
        "clock_notes": "Gateway timestamps are UTC. Archive timestamps are 2 minutes ahead; subtract 2 minutes. Login timestamps are UTC.",
        "access_rule": "Enabled owners may export their own collection. Enabled reviewers may read another collection but cannot export it. Disabled identities are denied.",
        "identities": [
            {"user": "Nia", "role": "owner", "enabled": True, "collection": "cobalt"},
            {"user": "Sol", "role": "reviewer", "enabled": True, "collection": "amber"},
        ],
        "gateway": [
            {
                "id": "g1",
                "utc": "02:00:00Z",
                "request": "x1",
                "user": "Nia",
                "operation": "export",
                "collection": "cobalt",
                "status": 200,
            },
            {
                "id": "g2",
                "utc": "02:01:00Z",
                "request": "x2",
                "user": "Sol",
                "operation": "export",
                "collection": "cobalt",
                "status": 403,
            },
            {
                "id": "g3",
                "utc": "02:01:10Z",
                "request": "x3",
                "user": "Sol",
                "operation": "read",
                "collection": "cobalt",
                "status": 200,
            },
            {
                "id": "g4",
                "utc": "02:02:00Z",
                "request": "x4",
                "user": "Nia",
                "operation": "export",
                "collection": "cobalt",
                "status": 200,
            },
        ],
        "archive": [
            {"id": "a1", "local": "02:02:20Z", "request": "x1", "event": "stored"},
            {"id": "a2", "local": "02:04:20Z", "request": "x4", "event": "stored"},
        ],
        "logins": [
            {"id": "s1", "utc": "01:59:10Z", "user": "Nia", "status": "failure"},
            {"id": "s2", "utc": "01:59:20Z", "user": "Nia", "status": "failure"},
            {"id": "s3", "utc": "01:59:30Z", "user": "Nia", "status": "success"},
        ],
        "trusted_manifest": {
            "request": "x1",
            "sha256": digest(reference),
            "encoding": "UTF-8",
            "content": reference,
        },
        "export_capture": {
            "request": "x1",
            "sha256": digest(exported),
            "content": exported,
        },
        "archive_capture": {"request": "x1", "sha256": digest(copy), "content": copy},
        "report": "The complainant points to Sol’s 403, Nia’s failed logins and a differently named archive. They assert one attacker changed the content and took all services offline.",
        "followup_condition": "On a copy, disable Nia and grant Sol the owner role for cobalt. Keep the archive bytes identical but rename its file. Re-evaluate each relevant control.",
    }
    expected = {
        "archive_utc": "02:00:20Z",
        "join": "g1",
        "order": "s3,g1,a1,g2,g3,g4,a2",
        "manifest_match": variant == 0,
        "transit_change": variant == 1,
        "first_divergence": ["none", "between export and archive", "at export"][
            variant
        ],
        "denied_export": "g2",
        "legitimate_control": "g1",
        "read_control": "g3",
        "unavailable": False,
        "login_attribution": "insufficient evidence",
        "disabled_owner_export": False,
        "new_owner_export": True,
        "rename_fixes_match": variant == 0,
    }
    fields = {
        "archive_utc": field("UTC timestamp of a1 (HH:MM:SSZ)"),
        "join": field(
            "Gateway record sharing a1’s request ID", "select", ["g1", "g2", "g3", "g4"]
        ),
        "order": field("Order s3, g1, g2, g3, g4, a1 and a2 in UTC, comma separated"),
        "manifest_match": field(
            "Does the archived x1 content match the trusted manifest?", "boolean"
        ),
        "transit_change": field(
            "Did x1 bytes change BETWEEN the export capture and archive capture?",
            "boolean",
        ),
        "first_divergence": field(
            "Earliest captured divergence from the trusted manifest",
            "select",
            ["none", "at export", "between export and archive"],
        ),
        "denied_export": field(
            "Record of a correctly denied non-owner export",
            "select",
            ["g1", "g2", "g3", "g4"],
        ),
        "legitimate_control": field(
            "Earliest successful authorized export control",
            "select",
            ["g1", "g2", "g3", "g4"],
        ),
        "read_control": field(
            "Record showing the reviewer can still read",
            "select",
            ["g1", "g2", "g3", "g4"],
        ),
        "unavailable": field(
            "Do these captures support the claim that ALL services were unavailable?",
            "boolean",
        ),
        "login_attribution": field(
            "What can these login records prove about malicious intent?",
            "select",
            ["confirmed malicious", "confirmed benign", "insufficient evidence"],
        ),
        "disabled_owner_export": field(
            "Changed condition: may disabled Nia export?", "boolean"
        ),
        "new_owner_export": field(
            "Changed condition: may enabled Sol, now cobalt’s owner, export?", "boolean"
        ),
        "rename_fixes_match": field(
            "Changed condition: after renaming identical archive bytes, do they match the trusted manifest?",
            "boolean",
        ),
    }
    return result(
        item["brief"]
        + " Build a UTC sequence, compare each capture with its reference, and test each allegation independently. Use your notebook for competing explanations; submit the verifiable comparisons below.",
        data,
        expected,
        fields,
        "Subtract the archive’s two-minute offset before ordering; a1 joins g1 by x1, not by the closest printed timestamp. g2 is an expected policy denial, while g1 and g3 preserve legitimate export and read. "
        + [
            "The archive matches both earlier captures. A new filename supplies no evidence of changed bytes.",
            "The export matched the trusted manifest, but the archive did not: the first observed difference lies between those captures. This locates a boundary, not an actor.",
            "The export already used CRLF where the trusted manifest used LF. The archive matches the export, so calling it a transit modification is unsupported.",
        ][variant]
        + " Failure-then-success logins permit both benign and malicious explanations. Neither those logins nor content differences establish who acted. Disabled-owner and newly-authorized-owner predictions must follow the unchanged policy.",
        transfer=True,
        followup="byte-change",
    )


def generate(item, now, variant=0):
    if item["family"] in {"python", "spatial"}:
        from ascend.playground.subjects import generate as subject_generate

        return subject_generate(item, variant)
    id, family = item["id"], item["family"]
    if item["role"] == "example":
        intro, data, explanation, followup = EXAMPLES[family]
        return result(intro, data, {}, {}, explanation, followup=followup)
    if item["kind"] == "free":
        return result(
            "Edit the inputs, inspect the outcome, then save your workspace. Reset creates a separate copy.",
            workspace_fixture(family),
            {},
            {},
            "",
        )
    if item["format"] == "mystery":
        return mystery(item, variant)
    if family == "access":
        requests = policy_fixture(12 if id == "policy-audit" else 6)
        expected = {r["id"]: access_decision(r)[0] for r in requests}
        fields = {r["id"]: field(f"Allow {r['id']}?", "boolean") for r in requests}
        data = {"requests": requests}
        if item["format"] in {"transfer", "repair"}:
            changed = deepcopy(requests[0])
            changed["enabled"] = not changed["enabled"]
            data["changed_request"] = changed
            expected["changed"] = access_decision(changed)[0]
            fields["changed"] = field("Allow the changed request?", "boolean")
        if item["format"] == "repair":
            data["candidate_policies"] = {
                "A": "Allow every admin write",
                "B": "Deny disabled; owners read/write; admins read only others’ files",
                "C": "Deny every write",
            }
            fields["repair"] = field(
                "Which policy preserves legitimate owner writes and prevents unrelated writes?",
                "select",
                ["A", "B", "C"],
            )
            expected["repair"] = "B"
        explanation = " ".join(f"{r['id']}: {access_decision(r)[1]}" for r in requests)
        return result(
            "Disabled identities are denied first. Enabled owners read/write; enabled admins may read others’ files, but not write them. Evaluate every request.",
            data,
            expected,
            fields,
            explanation
            + " Denying all writes would also break the legitimate owner control.",
            transfer=item["format"] != "exercise",
            followup="request-change",
        )
    if family == "subnet":
        fixture = native_generate("subnet", None, now)
        data, expected = fixture["public"]["data"], fixture["expected"]
        fields = {
            k: field(
                k.replace("_", " ").capitalize(),
                "integer" if type(v) is int else "text",
            )
            for k, v in expected.items()
        }
        if id == "address-capacity":
            hosts = secrets.choice([15, 29, 31, 60, 65, 110])
            data["required_hosts"] = hosts
            expected = {
                "prefix": next(
                    p for p in range(30, 23, -1) if 2 ** (32 - p) - 2 >= hosts
                ),
                "fits": hosts <= fixture["expected"]["usable_hosts"],
            }
            fields = {
                "prefix": field(
                    "Largest prefix length (smallest subnet) that fits the required hosts",
                    "integer",
                ),
                "fits": field("Does the supplied interface subnet fit?", "boolean"),
            }
        if id == "network-plan":
            data["requirements"] = {
                "users": 60,
                "services": 25,
                "management": 12,
                "parent": "192.0.2.0/24",
                "allocation": "Allocate largest first, starting at .0 with no gaps.",
            }
            expected.update(
                users="192.0.2.0/26",
                services="192.0.2.64/27",
                management="192.0.2.96/28",
                remaining=144,
            )
            fields.update(
                {
                    k: field(f"{k.capitalize()} CIDR")
                    for k in ("users", "services", "management")
                }
            )
            fields["remaining"] = field(
                "Unallocated addresses in the /24 after those three blocks", "integer"
            )
        return result(
            "Find the requested boundaries and capacities. For ordinary IPv4 subnets reserve the network and broadcast addresses. Use canonical CIDR notation.",
            data,
            expected,
            fields,
            "A /p has 2^(32-p) total addresses and two fewer ordinary usable hosts. Locate the aligned block containing the supplied address. Capacity must include reserved addresses; adjacent allocated segments must not overlap.",
            transfer=id == "address-capacity",
            followup="address-capacity",
        )
    if family == "logging":
        marker = secrets.choice(["delivery", "worker", "report"])
        events = [
            {
                "id": f"e{i + 1}",
                "marker": marker if i < 6 else "health",
                "status": secrets.choice([200, 200, 403, 503]),
                "window": "before" if i % 2 == 0 else "after",
                "time": f"09:00:{i * 5:02d}Z",
            }
            for i in range(9)
        ]
        expected = {
            "errors": sum(e["status"] >= 400 and e["marker"] == marker for e in events)
        }
        fields = {
            "errors": field(
                "How many failures belong to the selected marker?", "integer"
            )
        }
        if id != "event-filter":
            expected.update(
                before=sum(
                    e["status"] >= 400
                    and e["marker"] == marker
                    and e["window"] == "before"
                    for e in events
                ),
                changed=sum(
                    e["status"] >= 400 and e["marker"] == marker
                    for e in events
                    if e["id"] != "e1"
                ),
            )
            fields.update(
                before=field(
                    "How many selected-marker failures occurred before?", "integer"
                ),
                changed=field(
                    "If e1 becomes a success, how many selected-marker failures remain?",
                    "integer",
                ),
            )
        if id == "release-review":
            expected.update(
                first="e1",
                conclusion="insufficient evidence",
                rollback=sum(
                    e["marker"] == marker
                    and e["window"] == "after"
                    and e["status"] >= 500
                    for e in events
                ),
            )
            fields.update(
                first=field("Earliest selected-marker event ID"),
                conclusion=field(
                    "Do these records alone prove the release caused every failure?",
                    "select",
                    ["proven", "insufficient evidence"],
                ),
                rollback=field(
                    "With rollback eliminating only 5xx errors in the after window, how many after-window errors would it remove?",
                    "integer",
                ),
            )
        secrets.SystemRandom().shuffle(events)
        return result(
            "Filter by the supplied marker. Status >= 400 is a failure. Compare the full captured stream before making a claim about a release.",
            {"marker": marker, "events": events},
            expected,
            fields,
            "Count only the selected marker, then compare windows. A healthy unrelated request cannot erase a failure. The changed-event count removes e1 only if it failed. Time correlation alone cannot establish that a release caused an error.",
            transfer=id != "event-filter",
            followup="event-compare",
        )
    if family == "integrity":
        value = f"evidence={secrets.randbelow(1000)}\n"
        change = secrets.choice(["newline", "space", "rename"])
        copy = (
            value.rstrip("\n")
            if change == "newline"
            else value + " "
            if change == "space"
            else value
        )
        data = {
            "trusted_content": value,
            "copy_content": copy,
            "copy_name": "archive.txt",
            "encoding": "UTF-8",
        }
        expected = {"matches": value == copy, "copy_sha256": digest(copy)}
        fields = {
            "matches": field("Are these exact bytes equal?", "boolean"),
            "copy_sha256": field("SHA-256 of copy_content (use the text calculator)"),
        }
        if id != "copy-check":
            data["changed_copy"] = copy + "\n"
            expected["changed_matches"] = data["changed_copy"] == value
            fields["changed_matches"] = field(
                "Does changed_copy match trusted_content?", "boolean"
            )
        if id == "evidence-review":
            data["events"] = [
                {"id": "a", "time": "08:00:03Z", "action": "copy received"},
                {"id": "b", "time": "08:00:01Z", "action": "trusted digest recorded"},
                {"id": "c", "time": "08:00:02Z", "action": "copy sent"},
            ]
            expected.update(
                order="b,c,a",
                attribution="insufficient evidence",
                filename_changes_digest=False,
            )
            fields.update(
                order=field("Event IDs in order, separated by commas"),
                attribution=field(
                    "Do byte differences identify who changed the file?",
                    "select",
                    ["yes", "insufficient evidence"],
                ),
                filename_changes_digest=field(
                    "Would renaming the same bytes change the digest?", "boolean"
                ),
            )
        return result(
            "Compare the exact UTF-8 bytes, including whitespace. The reference is trusted separately. The calculator accepts text but does not choose which evidence supports your conclusion.",
            data,
            expected,
            fields,
            "Equal bytes produce equal SHA-256 digests. Adding or removing whitespace changes the bytes; renaming does not. A differing digest shows a mismatch, not its author or intent. Compare the changed copy again instead of reusing your first conclusion.",
            transfer=id != "copy-check",
            followup="byte-change",
        )
    if family == "timeline":
        failures = 3 + secrets.randbelow(8)
        spacing = 3 + secrets.randbelow(24)
        base = now.replace(microsecond=0) - timedelta(minutes=5)
        events = [
            {
                "id": f"e{i + 1}",
                "actor": "Ari",
                "status": "failure",
                "time": (base + timedelta(seconds=i * spacing)).isoformat(),
            }
            for i in range(failures)
        ]
        events.append(
            {
                "id": "success",
                "actor": "Ari",
                "status": "success",
                "time": (base + timedelta(seconds=failures * spacing)).isoformat(),
            }
        )
        expected = {
            "failures": failures,
            "within_minute": failures >= 5 and (failures - 1) * spacing <= 60,
            "changed": False,
        }
        fields = {
            "failures": field("Failures before success", "integer"),
            "within_minute": field(
                "Do ALL the failures form a group of at least five within 60 seconds?",
                "boolean",
            ),
            "changed": field(
                "If the success is moved before every failure, is this still a failure-then-success sequence?",
                "boolean",
            ),
        }
        secrets.SystemRandom().shuffle(events)
        return result(
            "Sort the timestamps and inspect the stated pattern. This is an investigation lead, not proof of compromise.",
            {"events": events},
            expected,
            fields,
            "Count failures, then subtract the earliest failure time from the latest. Both the count and the window must fit. Moving success before them breaks the stated sequence; it does not prove anything about intent.",
            transfer=True,
            followup="event-order",
        )
    raise ValueError("Unsupported activity family")


def fixture_key(item, fixture, variant):
    if item["variant_strategy"] == "authored" or item["role"] == "example":
        return f"{item['id']}:v{item['version']}:{variant}"
    data = deepcopy(fixture["public"]["data"])
    if item["family"] == "access" and item["kind"] != "free":
        # Identity renaming and shuffled display order do not make a fresh case.
        data = sorted(
            (r["caller"] == r["owner"], r["role"], r["enabled"], r["action"])
            for r in data["requests"]
        )
    elif item["family"] == "logging" and item["kind"] != "free":
        data = sorted(
            (e["id"], e["marker"] == data["marker"], e["status"], e["window"])
            for e in data["events"]
        )
    elif item["family"] == "timeline" and item["kind"] != "free":
        # Absolute dates and shuffled event order are not novel reasoning.
        events = sorted(data["events"], key=lambda e: e["time"])
        from datetime import datetime

        start = datetime.fromisoformat(events[0]["time"])
        data = [
            (e["status"], (datetime.fromisoformat(e["time"]) - start).total_seconds())
            for e in events
        ]
    return digest(json.dumps(data, sort_keys=True))


def evaluate(fixture, answers):
    if not isinstance(answers, dict):
        raise ValueError("Answers must be a JSON object")
    expected = fixture["expected"]
    if set(answers) != set(expected):
        raise ValueError("Answer every evidence check using the supplied field names")
    for key, value in expected.items():
        answer = answers[key]
        if type(answer) is not type(value):
            raise ValueError(f"{key} requires a {type(value).__name__} value")

    def normalize(value):
        return ",".join(part.strip().lower() for part in value.split(","))

    return all(
        (normalize(answers[k]) == normalize(v))
        if isinstance(v, str)
        else answers[k] == v
        for k, v in expected.items()
    )
