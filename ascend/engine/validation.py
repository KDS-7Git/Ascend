import re

SECRET = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{32}(?![A-Za-z0-9])|(?:flag|picoCTF|THM)\{", re.I)


def guard_secrets(*values):
    if any(SECRET.search(str(v)) for v in values if v):
        raise ValueError("Possible password or flag detected; remove secrets before saving")


def validate_entry(learned, next_step, proof=None, previous=None, minutes=None, manual=True, minimum=20):
    if not isinstance(learned, str) or not isinstance(next_step, str):
        raise ValueError("Learned and next step must be text")
    learned, next_step = learned.strip(), next_step.strip()
    guard_secrets(learned, next_step, proof)
    if not learned or (manual and len(learned) < minimum):
        raise ValueError(f"What you learned must contain at least {minimum} characters")
    if not next_step:
        raise ValueError("A next step is required")
    if manual and learned == previous:
        raise ValueError("What you learned must differ from the previous entry")
    if minutes is not None and (type(minutes) is not int or minutes <= 0 or minutes > 1440):
        raise ValueError("Minutes must be between 1 and 1440")
    return learned, next_step
