"""Authored instruction for separate examples, never independent assessments."""


def step(
    title, body, evidence=None, question=None, choices=(), answer=0, explanation=""
):
    return dict(
        title=title,
        body=body,
        evidence=evidence,
        question=question,
        choices=list(choices),
        answer=answer,
        explanation=explanation,
    )


LESSONS = {
    "access": [
        step(
            "Read the rule before the request",
            "Your goal is to decide whether one request is allowed. Check disabled identities first, then ownership, then the admin exception. You can do everything on this page.",
            {
                "policy": "Disabled → deny. Enabled owner → read/write. Other enabled admin → read only."
            },
        ),
        step(
            "Follow one request",
            "Mira is enabled, but Dev owns the file. Mira is an admin trying to write. The admin exception only permits reading.",
            {
                "caller": "Mira",
                "owner": "Dev",
                "enabled": True,
                "role": "admin",
                "action": "write",
            },
            "Is this write allowed?",
            ["No", "Yes"],
            0,
            "No. Being an admin does not grant write access to another owner's file.",
        ),
        step(
            "Change just one condition",
            "Keep the caller, owner and role the same. Change the action from write to read.",
            None,
            "What changes?",
            ["The request is allowed", "The request is still denied"],
            0,
            "The enabled admin can read. If you disable Mira instead, both requests are denied: the first rule takes priority.",
        ),
    ],
    "subnet": [
        step(
            "Find the size of a block",
            "Your goal is to find the network containing 192.0.2.70/26. IPv4 has 32 bits; /26 leaves 6 host bits. Each block contains 2⁶ = 64 addresses.",
            {"block_starts": [0, 64, 128, 192]},
        ),
        step(
            "Place the address in a block",
            "70 falls between 64 and 127. The first address is the network; the last is broadcast.",
            {"network": "192.0.2.64/26", "broadcast": "192.0.2.127"},
            "Which range can ordinary hosts use?",
            [".65 through .126", ".64 through .127"],
            0,
            "Exclude the network and broadcast addresses: 64 − 2 = 62 usable hosts.",
        ),
        step(
            "Check a changed prefix",
            "A /27 leaves 5 host bits, so it has 32 addresses. Subtract two for an ordinary subnet.",
            None,
            "How many usable hosts fit in /27?",
            ["32", "30"],
            1,
            "30. Choose a subnet by usable capacity, not by the last octet of an interface.",
        ),
    ],
    "logging": [
        step(
            "Choose the events that belong together",
            "Your goal is to count failures for the blue request marker. A marker connects related events; an unrelated error should not change this count.",
            [
                {"id": "e1", "marker": "blue", "status": 200},
                {"id": "e2", "marker": "blue", "status": 503},
                {"id": "e3", "marker": "amber", "status": 404},
            ],
        ),
        step(
            "Filter, then count",
            "Keep e1 and e2 because they have marker blue. In this exercise, a status of 400 or higher is a failure.",
            None,
            "How many blue events failed?",
            ["One", "Two"],
            0,
            "Only e2 failed. e3 is an error, but it belongs to amber.",
        ),
        step(
            "Notice what a filter hides",
            "Now imagine filtering to status=200 before checking for errors.",
            None,
            "Does an empty error panel prove there were no failures?",
            ["Yes", "No"],
            1,
            "No. That filter removed the failed events. Compare against the full stream before drawing a conclusion.",
        ),
    ],
    "integrity": [
        step(
            "Compare content, not filenames",
            "Your goal is to identify the unchanged copy. SHA-256 turns exact file bytes into a digest: changing even an invisible newline changes that digest. No files need to be created or downloaded.",
            {
                "trusted content (escaped)": '"note\\n"',
                "copy A (escaped)": '"note\\n"',
                "copy B (escaped)": '"note"',
            },
        ),
        step(
            "Spot the invisible difference",
            "Here \\n represents one newline character. It is part of the content, not decoration. The trusted content and A each have five UTF-8 bytes; B has four.",
            None,
            "Which copy matches the trusted content?",
            ["Copy A", "Copy B", "Both copies"],
            0,
            "A matches. B is missing the final newline, so its SHA-256 digest differs even though the visible word looks identical.",
        ),
        step(
            "Know what a digest can prove",
            "A trusted reference digest helps check whether bytes match. A digest alone does not tell you who created a file or whether its source is trustworthy.",
            None,
            "If someone renames copy A, do its bytes or digest change?",
            ["No", "Yes"],
            0,
            "No. Renaming does not edit the content. Trust in the reference must come from a separate source; SHA-256 does not authenticate an author.",
        ),
    ],
    "timeline": [
        step(
            "Put events in time order",
            "Your goal is to describe what happened without guessing intent. All three timestamps use the same time basis.",
            [
                {"id": "a", "time": "09:00:20", "status": "success"},
                {"id": "b", "time": "09:00:00", "status": "failure"},
                {"id": "c", "time": "09:00:10", "status": "failure"},
            ],
        ),
        step(
            "Describe the sequence",
            "Sort from earliest to latest: b, c, a. Two failures are followed by a success within twenty seconds.",
            None,
            "Does this prove an attacker logged in?",
            ["No", "Yes"],
            0,
            "No. Someone correcting a mistyped password also fits these events. The sequence is a lead, not proof of intent.",
        ),
        step(
            "Test the explanation",
            "Imagine that the success happened before both failures.",
            None,
            "Would 'failures followed by success' still describe it?",
            ["Yes", "No"],
            1,
            "No. Order matters. Normalize timestamps first and ask for independent evidence before attributing intent.",
        ),
    ],
    "python": [
        step(
            "Trace a loop one value at a time",
            "Your goal is to predict the output without running code. Start with an empty list. For each input value, append it only if the condition is true.",
            {
                "values": [2, 5, 5, 8],
                "code": "selected = []\nfor value in values:\n    if value >= 5:\n        selected.append(value)",
            },
        ),
        step(
            "Keep both boundary values",
            "2 fails. The first 5 passes, and the second 5 passes separately. Finally 8 passes. A list preserves duplicates and order.",
            None,
            "What is selected?",
            ["[5, 8]", "[5, 5, 8]"],
            1,
            "[5, 5, 8]: three items with a sum of 18. append adds each matching value.",
        ),
        step(
            "Change the comparison",
            "Replace >= 5 with > 5. Values equal to 5 now fail.",
            None,
            "What remains?",
            ["[8]", "[5, 5, 8]"],
            0,
            "Only [8]. With an empty input the loop visits no values, leaving [].",
        ),
    ],
    "spatial": [
        step(
            "Read the transform order",
            "Your goal is to find a point's world position. Start at local [1, 2, −1], scale by 2, then translate by [3, 0, 1]. Work on each axis separately.",
            {"rule": "world = 2 × local + translation"},
        ),
        step(
            "Scale, then translate",
            "Scaling gives [2, 4, −2]. Now add [3, 0, 1] coordinate by coordinate.",
            None,
            "Where is the point now?",
            ["[5, 4, −1]", "[8, 4, 0]"],
            0,
            "[2+3, 4+0, −2+1] = [5, 4, −1].",
        ),
        step(
            "Try the reverse order",
            "Translating first gives [4, 2, 0]. Scaling that result gives [8, 4, 0]. The translation got scaled too.",
            None,
            "Does reversing the operations preserve the position here?",
            ["Yes", "No"],
            1,
            "No. The order is part of the rule. A useful control is the local origin: scale then translate maps it to [3, 0, 1].",
        ),
    ],
}

REFLECTIONS = {
    "access": "Explain why an enabled admin can read another owner's file but cannot write it.",
    "subnet": "Explain how you found the /26 block and why it has 62 usable hosts.",
    "logging": "Explain why the blue failure count is one, and what a status filter could hide.",
    "integrity": "Explain why copy B differs, and why a matching digest does not prove who created a file.",
    "timeline": "Describe the event order and one reason it does not prove an attack.",
    "python": "Explain why both 5 values stay in the output and what changes with > instead of >=.",
    "spatial": "Explain why scaling then translating gives a different result from the reverse order.",
}


def steps(family):
    return LESSONS[family]
