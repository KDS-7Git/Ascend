"""Python and spatial reasoning content; constrained data, never learner code."""

import secrets

from ascend.playground.fixtures import field, result


def generate(item, variant=0):
    if item["role"] == "example":
        if item["family"] == "python":
            return result(
                "A loop visits values in order. A condition decides which values enter the output list; append adds a value without replacing earlier ones.",
                {
                    "values": [2, 5, 5, 8],
                    "code": "selected = []\nfor value in values:\n    if value >= 5:\n        selected.append(value)\nprint(selected)",
                },
                {},
                {},
                "2 fails the condition. Both 5 values and 8 pass, so selected is [5, 5, 8]. The output has length 3 and sum 18. Replacing >= with > excludes both boundary values, leaving [8]. An empty input produces an empty output. A loop continues until its input ends unless control flow explicitly returns or breaks.",
                followup="python-trace",
            )
        return result(
            "A local point describes a position relative to its object. A translation adds an offset on each axis. A uniform scale multiplies every coordinate. Apply operations in the stated order.",
            {
                "local_xyz": [1, 2, -1],
                "scale": 2,
                "translation_xyz": [3, 0, 1],
                "rule": "world = scale * local + translation",
            },
            {},
            {},
            "Scaling first gives [2, 4, -2]; translating then gives [5, 4, -1]. Translating first and scaling instead gives [8, 4, 0], because the translation is scaled too. The local origin maps to [3, 0, 1] under the intended rule. In an orthographic front view, x and y determine framing; the stated camera bounds include their edges.",
            followup="spatial-translate",
        )
    if item["id"] == "desk-39":
        return contact_sheet(item, variant)
    if item["id"] == "studio-52":
        return displaced_prop(item, variant)
    return python_fixture(item) if item["family"] == "python" else spatial_fixture(item)


def python_fixture(item):
    if item["id"] in {"python-trace", "python-boundary"}:
        threshold = secrets.randbelow(7) + 2
        values = [
            threshold,
            threshold - 1,
            threshold + 2,
            threshold,
            secrets.randbelow(12),
        ]
        secrets.SystemRandom().shuffle(values)
        selected = [v for v in values if v >= threshold]
        data = {
            "values": values,
            "code": f"selected = []\nfor value in values:\n    if value >= {threshold}:\n        selected.append(value)\nprint(selected)",
        }
        expected = {
            "count": len(selected),
            "total": sum(selected),
            "first": selected[0],
        }
        fields = {
            "count": field("Number of selected values", "integer"),
            "total": field("Sum of selected values", "integer"),
            "first": field("First selected value", "integer"),
        }
        if item["format"] == "transfer":
            expected.update(
                strict_count=sum(v > threshold for v in values),
                appended_count=len(selected) + 1,
                empty_count=0,
            )
            fields.update(
                strict_count=field(
                    "If >= becomes >, how many values are selected?", "integer"
                ),
                appended_count=field(
                    f"If one extra {threshold} is appended to the ORIGINAL input, how many values pass >=?",
                    "integer",
                ),
                empty_count=field(
                    "How many values pass when the input list is empty?", "integer"
                ),
            )
        return result(
            "Trace the supplied Python code without running it. Preserve duplicate values and their input order.",
            data,
            expected,
            fields,
            "A filter tests each value separately and keeps duplicates that pass. >= includes values equal to the threshold; > excludes them. Append preserves earlier matches, and empty input runs the loop zero times.",
            transfer=item["format"] == "transfer",
            followup="python-boundary",
        )
    names = ["draft.txt", "cover.PNG", "notes.txt", "portrait.png", "readme.md"]
    occupied = secrets.choice(["draft.txt", "notes.txt"])
    files = [
        {"id": f"f{i + 1}", "name": name, "bytes": 10 + secrets.randbelow(90)}
        for i, name in enumerate(names)
    ]
    data = {
        "files": files,
        "existing_destinations": [f"text/{occupied}"],
        "rule": "A filename ending in .txt goes to text/<name>; .png (case insensitive) goes to images/<name>. Other files stay in place. Skip a move if its destination already exists. The dry run prints plans and never changes files.",
        "candidate_repairs": {
            "A": "Overwrite an existing destination",
            "B": "Skip a collision and report it",
            "C": "Delete the source before checking the destination",
        },
    }
    expected = {
        "moves": 3,
        "planned_bytes": sum(
            f["bytes"]
            for f in files
            if f["name"] != occupied and f["name"].lower().endswith((".txt", ".png"))
        ),
        "collision": occupied,
        "repair": "B",
        "source_unchanged": True,
    }
    fields = {
        "moves": field("Number of proposed moves excluding collisions", "integer"),
        "planned_bytes": field(
            "Total bytes in all proposed moves, excluding collisions", "integer"
        ),
        "collision": field(
            "Filename whose move must be skipped",
            "select",
            ["draft.txt", "notes.txt", "cover.PNG"],
        ),
        "repair": field(
            "Policy that preserves both source and existing destination",
            "select",
            ["A", "B", "C"],
        ),
        "source_unchanged": field(
            "After a dry run, are the original source files still present?", "boolean"
        ),
    }
    if item["id"] == "organizer-review":
        expected.update(
            image_bytes=sum(
                f["bytes"] for f in files if f["name"].lower().endswith(".png")
            ),
            changed_moves=4,
            duplicate_moves=3,
            empty_moves=0,
        )
        fields.update(
            image_bytes=field("Total bytes in proposed image moves", "integer"),
            changed_moves=field(
                "If the occupied destination is removed, how many moves are proposed?",
                "integer",
            ),
            duplicate_moves=field(
                "If a duplicate of the colliding source is added while its destination remains occupied, how many moves are still proposed?",
                "integer",
            ),
            empty_moves=field("Moves for an empty source folder", "integer"),
        )
    return result(
        "Build a dry-run plan from the complete fixture. No files on your device are accessed or changed.",
        data,
        expected,
        fields,
        f"{occupied} collides with an existing destination and must stay at the source. Both PNG spellings qualify because the rule ignores suffix case; readme.md stays. A dry run reports decisions without mutating the fixture. Removing the collision permits one more move, while another colliding source does not.",
        transfer=item["format"] == "transfer",
        followup="python-boundary",
    )


def spatial_fixture(item):
    local = [secrets.randbelow(9) - 4 for _ in range(3)]
    offset = [secrets.randbelow(7) - 3 for _ in range(3)]
    if offset == [0, 0, 0]:
        offset[0] = 2
    scale = 1 if item["id"] == "spatial-translate" else secrets.choice([2, 3])
    world = [v * scale + d for v, d in zip(local, offset)]
    data = {
        "local_xyz": local,
        "translation_xyz": offset,
        "scale": scale,
        "rule": "Apply uniform scale first, then translation: world = scale * local + translation.",
    }
    expected = {axis: value for axis, value in zip(("x", "y", "z"), world)}
    fields = {axis: field(f"World {axis} coordinate", "integer") for axis in expected}
    if item["id"] == "spatial-order":
        changed = [(v + d) * scale for v, d in zip(local, offset)]
        expected.update(
            {f"changed_{axis}": value for axis, value in zip(("x", "y", "z"), changed)}
        )
        fields.update(
            {
                f"changed_{axis}": field(
                    f"If translation happens BEFORE scaling, what is world {axis}?",
                    "integer",
                )
                for axis in ("x", "y", "z")
            }
        )
    if item["id"] in {"spatial-frame", "scene-layout"}:
        data["camera"] = {
            "view": "Orthographic front view; points only, no object radius",
            "x_min": -5,
            "x_max": 5,
            "y_min": -5,
            "y_max": 5,
            "edges_included": True,
        }
        expected.update(
            visible=all(-5 <= v <= 5 for v in world[:2]),
            moved_visible=all(-5 <= v + 2 <= 5 for v in world[:2]),
        )
        fields.update(
            visible=field(
                "Is the point inside the camera frame, including its edges?", "boolean"
            ),
            moved_visible=field(
                "If only world x and y each increase by 2, does the point fit?",
                "boolean",
            ),
        )
    if item["id"] == "scene-layout":
        data["objects"] = [
            {"id": "A", "local_xyz": local},
            {"id": "B", "local_xyz": [0, 0, 0]},
            {"id": "C", "local_xyz": [-local[0], -local[1], local[2]]},
        ]
        positions = [
            [v * scale + d for v, d in zip(o["local_xyz"], offset)]
            for o in data["objects"]
        ]
        expected.update(
            visible_count=sum(all(-5 <= v <= 5 for v in p[:2]) for p in positions),
            min_x=min(p[0] for p in positions),
            max_x=max(p[0] for p in positions),
            origin_x=offset[0],
        )
        fields.update(
            visible_count=field(
                "How many of A, B and C fit the camera frame?", "integer"
            ),
            min_x=field("Smallest world x across the three points", "integer"),
            max_x=field("Largest world x across the three points", "integer"),
            origin_x=field(
                "Control: where does the local origin land on x?", "integer"
            ),
        )
    return result(
        "Work with exact coordinates in this prepared scene fixture. No Blender installation is required. Treat objects as points and use the stated inclusive camera bounds.",
        data,
        expected,
        fields,
        "Apply the same operations independently to x, y and z. Scaling before translation does not scale the translation. The origin is a useful control because scaling zero leaves only the offset. Orthographic front framing compares world x and y with the bounds, including exact boundary values.",
        transfer=item["format"] == "transfer",
        followup="spatial-order",
    )


def contact_sheet(item, variant):
    code = [
        "def images(names):\n    selected = []\n    for name in names:\n        if name.endswith('.png'):\n            selected.append(name)\n    return selected",
        "def images(names):\n    selected = []\n    for name in names:\n        if name.lower().endswith('.png'):\n            selected.append(name)\n            return selected\n    return selected",
        "def images(names):\n    selected = []\n    for name in names:\n        if name.lower().endswith('.png'):\n            selected.append(name)\n    return selected",
    ][variant]
    diagnoses = [
        "Uppercase suffixes are excluded",
        "The function returns after the first match",
        "The captured behavior matches the image-only requirement",
    ]
    observations = [
        {"id": "t1", "input": ["a.png", "b.png"], "output_count": [2, 1, 2][variant]},
        {"id": "t2", "input": ["c.PNG"], "output_count": [0, 1, 1][variant]},
        {"id": "t3", "input": ["notes.txt"], "output_count": 0},
    ]
    expected = {
        "conclusion": diagnoses[variant],
        "evidence": ["t2", "t1", "t3"][variant],
        "prediction": [2, 1, 3][variant],
        "control": 0,
    }
    fields = {
        "conclusion": field(
            "Which conclusion fits the captured behavior?", "select", diagnoses
        ),
        "evidence": field(
            "Which test exposes the fault, or explains the expected exclusion when no fault is present?",
            "select",
            ["t1", "t2", "t3"],
        ),
        "prediction": field(
            'Output count for ["x.png", "y.PNG", "z.png"] under the ORIGINAL function',
            "integer",
        ),
        "control": field(
            'After a correct repair, how many files should ["notes.txt"] contribute?',
            "integer",
        ),
    }
    return result(
        item["brief"],
        {
            "requirement": "Return every .png image, ignoring suffix case. Preserve input order; exclude other extensions.",
            "code": code,
            "captured_tests": observations,
            "report": "The operator expected the text note to appear alongside the images. Decide which part of that report is supported.",
        },
        expected,
        fields,
        [
            "t2 shows a PNG excluded only because suffix comparison is case-sensitive. t1 establishes that multiple lowercase matches are retained.",
            "t1 stops after one match although both filenames qualify; t2 proves uppercase normalization works. The return inside the loop ends the function early.",
            "The tests retain both matching images and normalize uppercase. t3 excludes a text note exactly as required; its absence is not an implementation fault.",
        ][variant]
        + " A repair must preserve the non-image exclusion control. The mixed-case three-file prediction distinguishes the candidate behaviors.",
        transfer=True,
        followup="python-boundary",
    )


def displaced_prop(item, variant):
    diagnoses = [
        "Translation is applied before scaling",
        "The translation is missing",
        "The measured transform matches the specification",
    ]
    transform = [lambda x: 2 * (x + 3), lambda x: 2 * x, lambda x: 2 * x + 3][variant]
    data = {
        "specification": "Uniform scale 2, then translation [3, 0, 0]. World = 2 * local + translation. The camera includes x and y from -5 through 5, including the boundaries.",
        "measured_probes": [
            {"id": "p0", "local_xyz": [0, 0, 0], "world_xyz": [transform(0), 0, 0]},
            {"id": "p1", "local_xyz": [1, 0, 0], "world_xyz": [transform(1), 0, 0]},
            {"id": "p2", "local_xyz": [0, 1, 0], "world_xyz": [transform(0), 2, 0]},
        ],
        "report": "The prop should use local [1, 0, 0]. The operator claims a point exactly on the camera boundary cannot be visible.",
    }
    expected = {
        "conclusion": diagnoses[variant],
        "evidence": "p0",
        "prediction_x": transform(2),
        "repair_origin_x": 3,
        "repaired_visible": True,
    }
    fields = {
        "conclusion": field(
            "Which explanation fits all measured probes?", "select", diagnoses
        ),
        "evidence": field(
            "Which origin probe isolates what happened to translation?",
            "select",
            ["p0", "p1", "p2"],
        ),
        "prediction_x": field(
            "Using the ORIGINAL measured behavior, predict world x for local [2, 0, 0]",
            "integer",
        ),
        "repair_origin_x": field(
            "After restoring the specification, what world x must the local origin have?",
            "integer",
        ),
        "repaired_visible": field(
            "Under the specified transform, is local [1, 0, 0] within the inclusive camera frame?",
            "boolean",
        ),
    }
    return result(
        item["brief"],
        data,
        expected,
        fields,
        [
            "p0 lands at 6: the translation of 3 was scaled by 2. p1 at 8 confirms translation-before-scale.",
            "p0 stays at zero while p1 doubles; scaling works but the translation is absent.",
            "p0 lands at 3 and p1 at 5, matching scale-then-translate. A point at x=5 is inside the stated inclusive camera bounds.",
        ][variant]
        + " Restoring the specified transform must map the origin to x=3 and the prop to x=5. Preserve that legitimate framing control instead of removing the transform.",
        transfer=True,
        followup="spatial-order",
    )
