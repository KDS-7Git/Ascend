"""Saved result feedback, replay and motion controls in the real browser UI."""

import os
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright
from test_integration import live_server as live_server_fixture

from ascend.engine.packs import dump_toml

live_server = live_server_fixture

MOTION_CAPTURE = """
window.rewardAnimations = [];
const originalAnimate = Element.prototype.animate;
Element.prototype.animate = function(frames, options) {
  if (this.closest?.('[data-reward-kind]')) window.rewardAnimations.push(options.duration);
  return originalAnimate.call(this, frames, options);
};
"""


def capture(result, name):
    if folder := os.environ.get("ASCEND_UI_CAPTURE_DIR"):
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True)
        result.screenshot(path=str(path / f"{name}.png"), animations="disabled")


@pytest.mark.parametrize("width", [390, 1440])
def test_example_earns_practice_points_and_restores_without_motion(live_server, width):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 950}, reduced_motion="no-preference"
        )
        page.add_init_script(MOTION_CAPTURE)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        run = page.request.post(
            live_server + "/api/playground/activities/example-access/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + run["id"])
        page.get_by_role("button", name="Skip tour", exact=True).click()
        page.get_by_label("In your own words: what did you learn?").fill(
            "The caller needs ownership or a permitted administrator action."
        )
        page.get_by_role("button", name="Finish example", exact=True).click()
        result = page.locator(".pg-completion")
        expect(result).to_have_attribute("data-reward-kind", "example")
        expect(result).to_contain_text("+5 Practice points")
        expect(result.locator(".reward-xp")).to_have_count(0)
        expect(result).to_be_focused()
        assert page.evaluate("rewardAnimations.length") > 0
        capture(result, f"example-{width}")
        balances = page.request.get(live_server + "/api/rewards").json()
        assert balances["practice"]["total"] == 5 and balances["xp"]["total"] == 0
        page.reload()
        expect(result).to_be_visible()
        expect(page.locator("#route-progress")).not_to_be_visible()
        assert page.evaluate("rewardAnimations.length") == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()


@pytest.mark.parametrize("width,motion", [(390, "no-preference"), (1440, "reduce")])
def test_milestone_waits_for_save_names_the_work_and_keeps_replay_cosmetic(
    live_server, pack_data, width, motion
):
    pack_data["node"][0]["milestone"] = True
    pack_data["node"][0]["title"] = "Recover the service and preserve its state"
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 950}, reduced_motion=motion
        )
        page.add_init_script(MOTION_CAPTURE)
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start timed task", exact=True).click()
        page.locator(".lab-toolbar").get_by_role(
            "button", name="Notes & evidence", exact=True
        ).click()
        page.get_by_label("Your notes", exact=True).fill(
            "I restarted the service and retrieved the same update from its database."
        )
        page.route(
            "**/complete",
            lambda route: route.fulfill(
                status=500, json={"detail": "The completion could not be saved."}
            ),
        )
        page.locator(".notebook-complete").click()
        expect(page.locator("#notice")).to_contain_text("could not be saved")
        expect(page.locator(".lab-celebration")).to_have_count(0)
        assert (
            page.request.get(live_server + "/api/rewards").json()["practice"]["total"]
            == 0
        )
        page.unroute("**/complete")
        page.locator(".notebook-complete").click()
        result = page.locator(".lab-celebration")
        expect(result).to_have_attribute("data-reward-kind", "milestone")
        expect(result).to_contain_text("Recover the service and preserve its state")
        expect(result).to_contain_text("Completion recorded by you")
        expect(result).to_contain_text("+5 Practice points")
        expect(result.locator(".reward-medal")).to_be_visible()
        capture(result, f"milestone-{width}-{motion}")
        balances = page.request.get(live_server + "/api/rewards").json()
        assert balances["milestones"]["total"] == 1 and balances["xp"]["total"] == 0
        if motion == "reduce":
            assert page.evaluate("rewardAnimations.length") == 0
            expect(
                result.get_by_role(
                    "button", name="Replay celebration; recorded XP stays the same"
                )
            ).to_have_count(0)
        else:
            assert page.evaluate("rewardAnimations.length") > 0
            page.wait_for_timeout(1350)
            animations = page.evaluate("rewardAnimations.length")
            result.get_by_role(
                "button", name="Replay celebration; recorded XP stays the same"
            ).click()
            assert page.evaluate("rewardAnimations.length") > animations
            assert (
                page.request.get(live_server + "/api/rewards").json()["practice"][
                    "total"
                ]
                == 5
            )
        page.reload()
        expect(result).to_be_visible()
        expect(page.locator("#route-progress")).not_to_be_visible()
        assert page.evaluate("rewardAnimations.length") == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("width,motion", [(390, "no-preference"), (1440, "reduce")])
def test_correct_answer_uses_a_small_external_toast_and_optional_explanation(
    live_server, pack_data, width, motion
):
    pack_data["node"][0]["verify"] = {
        "type": "lab",
        "exercise": "case",
        "case_id": "ethical-hacking-foundations:foundations",
    }
    response = httpx.post(
        live_server + "/api/packs",
        files={"file": ("test.toml", dump_toml(pack_data), "text/plain")},
    )
    assert response.status_code == 200
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 950}, reduced_motion=motion
        )
        page.add_init_script(MOTION_CAPTURE)
        page.goto(live_server)
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start verified exercise", exact=True).click()
        page.get_by_role(
            "radio", name="Not yet. Record that the tool is installed", exact=False
        ).check()
        page.get_by_role("button", name="Submit answer", exact=True).click()
        toast, result = (
            page.locator(".answer-reward-toast"),
            page.locator(".case-feedback"),
        )
        expect(toast).to_be_visible()
        expect(toast).to_contain_text("+100 XP")
        expect(toast).to_contain_text("+5 Practice points")
        assert toast.evaluate("el => !el.closest('#challenge-content')")
        assert not page.evaluate(
            "Boolean(document.activeElement.closest('.answer-reward-toast'))"
        )
        assert toast.bounding_box()["height"] < 130
        assert result.bounding_box()["height"] < 180
        expect(result.locator(".reward-visual")).to_have_count(0)
        expect(result.locator("details")).not_to_have_attribute("open", "")
        explanation = result.get_by_text("A version command proves only", exact=False)
        expect(explanation).not_to_be_visible()
        expect(page.locator(".lab-celebration")).to_have_count(0)
        capture(toast, f"answer-{width}-{motion}")
        result.get_by_text("Why this answer?", exact=True).click()
        expect(explanation).to_be_visible()
        balances = page.request.get(live_server + "/api/rewards").json()
        assert balances["xp"]["total"] == 100 and balances["practice"]["total"] == 5
        if motion == "reduce":
            assert page.evaluate("rewardAnimations.length") == 0
        else:
            assert page.evaluate("rewardAnimations.length") > 0
        page.reload()
        expect(result).to_contain_text("Correct. Check complete.")
        expect(toast).to_have_count(0)
        assert page.evaluate("rewardAnimations.length") == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


def test_prediction_feedback_does_not_award_or_repeat(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 950})
        run = page.request.post(
            live_server + "/api/playground/activities/example-access/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + run["id"])
        page.get_by_role("button", name="Next step", exact=True).click()
        choice = page.get_by_role("button", name="No", exact=True)
        choice.click()
        toast, inline = (
            page.locator(".answer-reward-toast"),
            page.locator(".pg-prediction-feedback"),
        )
        expect(toast).to_be_visible()
        expect(toast.locator(".reward-receipt")).to_have_count(0)
        expect(inline).to_contain_text("That’s right.")
        assert inline.bounding_box()["height"] < 110
        expect(inline.locator("details")).not_to_have_attribute("open", "")
        original = toast.element_handle()
        choice.click()
        assert original.evaluate("el => el.isConnected")
        assert (
            page.request.get(live_server + "/api/rewards").json()["practice"]["total"]
            == 0
        )
        page.get_by_role("button", name="Next step", exact=True).click()
        expect(toast).to_have_count(0)
        browser.close()
