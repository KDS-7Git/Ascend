from types import SimpleNamespace

import pytest

from ascend.local_labs import wrongsecrets
from ascend.local_labs.catalog import detail, review_gaps


def test_service_check_requires_both_accepted_answer_and_rejected_control(monkeypatch):
    values = {
        "challenge_1": "one",
        "challenge_2": "two",
        "challenge_3": "three",
        "explanation": "Explain the secret exposure and the repair.",
    }
    runtime = SimpleNamespace(read_work=lambda *args, **kwargs: values)
    lab = wrongsecrets.WrongSecrets(runtime)
    row = {"port": 12345}
    monkeypatch.setattr(
        wrongsecrets,
        "answer",
        lambda port, number, value: value == values[f"challenge_{number}"],
    )
    result = lab.check(row)
    assert result["status"] == "pass" and result["authority"] == "local"
    for accepts in (True, False):
        monkeypatch.setattr(wrongsecrets, "answer", lambda *args, value=accepts: value)
        assert lab.check(row)["status"] == "fail"

    def missing(*args):
        raise OSError("Target disappeared")

    monkeypatch.setattr(wrongsecrets, "answer", missing)
    result = lab.check(row)
    assert result["status"] == "error" and {c["id"] for c in result["checks"]} == set(
        wrongsecrets.CHECK_IDS
    )


def test_upstream_answer_checker_does_not_treat_http_success_as_pass(monkeypatch):
    csrf = '<input name="_csrf" value="token">'
    response = {"status": 200, "body": '<div data-cy="success-alert">Correct</div>'}

    def request(port, path, *, data=None, cookie=None):
        if data is None:
            return 200, csrf, "JSESSIONID=test"
        assert data["_csrf"] == "token" and cookie == "JSESSIONID=test"
        return response["status"], response["body"], cookie

    monkeypatch.setattr(wrongsecrets, "request", request)
    assert wrongsecrets.answer(12345, 1, "value")
    response["body"] = '<div data-cy="incorrect-alert">Incorrect</div>'
    assert not wrongsecrets.answer(12345, 1, "value")
    for status, page in [
        (200, ""),
        (403, '<div data-cy="success-alert"></div>'),
        (
            200,
            '<div data-cy="success-alert"></div><div data-cy="incorrect-alert"></div>',
        ),
    ]:
        response.update(status=status, body=page)
        with pytest.raises(ValueError, match="unambiguous"):
            wrongsecrets.answer(12345, 1, "value")


def test_browser_session_and_csrf_are_required(monkeypatch):
    monkeypatch.setattr(
        wrongsecrets,
        "request",
        lambda *args, **kwargs: (200, "<html>not a challenge</html>", None),
    )
    with pytest.raises(ValueError, match="session and CSRF"):
        wrongsecrets.answer(12345, 1, "value")


def test_wrongsecrets_recipe_requires_both_images_and_runtime_evidence():
    recipe = detail("wrongsecrets-basics")
    assert "Subset proxy image needs a pinned digest" in review_gaps(
        {**recipe, "helper_image": {}}
    )
    assert "Container image digest is not pinned" in review_gaps(
        {**recipe, "image": {"reference": "latest"}}
    )
    assert "Lifecycle and negative/control tests need evidence" in review_gaps(
        {**recipe, "lifecycle_verified": False}
    )
