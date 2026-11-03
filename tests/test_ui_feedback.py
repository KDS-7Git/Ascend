"""User-visible handoffs, duration choices and feedback on a disposable server."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_integration import live_server as live_server_fixture

from ascend.application import Tracker
from ascend.engine.packs import dump_toml
from ascend.storage import Database

live_server = live_server_fixture


def capture(page, name):
    if folder := os.environ.get("ASCEND_UI_CAPTURE_DIR"):
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        expect(page.locator(".screen:not([hidden])")).not_to_have_attribute(
            "aria-busy", "true"
        )
        page.evaluate(
            "async () => { await Promise.all(document.getAnimations().filter(a => Number.isFinite(a.effect.getComputedTiming().endTime)).map(a => a.finished.catch(() => {}))); }"
        )
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(target / f"{name}.png"), full_page=True)


def accessibility(page):
    if script := os.environ.get("ASCEND_AXE_PATH"):
        page.evaluate(Path(script).read_text())
        result = page.evaluate(
            "async () => await axe.run(document, {runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21aa']}})"
        )
        assert not result["violations"], [
            (item["id"], [node["target"] for node in item["nodes"]])
            for item in result["violations"]
        ]


@pytest.mark.parametrize("width,theme", [(390, "dark"), (1440, "light")])
def test_walkthrough_hands_off_and_keeps_the_takeaway(live_server, width, theme):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})
        page.add_init_script(f"localStorage.setItem('ascend-theme', '{theme}')")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        run = page.request.post(
            live_server + "/api/playground/activities/example-access/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + run["id"])
        expect(
            page.get_by_role("heading", name="Read the rule before the request")
        ).to_be_visible()
        expect(page.locator(".pg-takeaway")).not_to_be_visible()
        page.get_by_role("button", name="Next step", exact=True).click()
        page.get_by_role("button", name="Yes", exact=True).click()
        expect(page.locator(".pg-prediction-feedback")).to_have_attribute(
            "data-feedback", "warning"
        )
        page.get_by_role("button", name="No", exact=True).click()
        expect(page.locator(".pg-prediction-feedback")).to_have_attribute(
            "data-feedback", "success"
        )
        capture(page, f"prediction-{width}-{theme}")
        page.get_by_role("button", name="Next step", exact=True).click()
        page.get_by_role("button", name="Finish walkthrough", exact=True).click()
        expect(page.locator(".pg-tour-finished")).to_have_attribute(
            "data-feedback", "success"
        )
        expect(page.locator(".pg-takeaway h2")).to_be_focused()
        expect(page.locator(".pg-takeaway")).to_be_visible()
        assert page.locator(".pg-takeaway").bounding_box()["y"] < 600
        note = "An enabled request still needs the owner or an administrator to be allowed."
        page.get_by_label("In your own words: what did you learn?").fill(note)
        page.get_by_role("button", name="Redo walkthrough", exact=True).click()
        expect(page.locator(".pg-takeaway")).not_to_be_visible()
        page.get_by_role("button", name="Skip tour", exact=True).click()
        expect(
            page.get_by_label("In your own words: what did you learn?")
        ).to_have_value(note)
        expect(page.locator("#pg-save-status")).to_contain_text("Saved")
        page.reload()
        expect(
            page.get_by_label("In your own words: what did you learn?")
        ).to_have_value(note)
        capture(page, f"takeaway-{width}-{theme}")
        page.get_by_role("button", name="Finish example", exact=True).click()
        expect(page.locator(".pg-completion")).to_have_attribute(
            "data-feedback", "success"
        )
        expect(page.locator(".pg-completion")).to_be_focused()
        expect(
            page.get_by_role("button", name="Try a separate challenge", exact=True)
        ).to_be_in_viewport()
        capture(page, f"completion-{width}-{theme}")
        accessibility(page)
        saved = page.request.get(
            live_server + "/api/playground/runs/" + run["id"]
        ).json()
        assert saved["result"]["xp"] == 0
        assert saved["status"] == "passed"
        page.reload()
        expect(page.locator(".pg-completion")).to_be_visible()
        assert (
            page.locator(".pg-completion").evaluate(
                "el => el.getAnimations({subtree:true}).length"
            )
            == 0
        )
        page.get_by_role("button", name="Try a separate challenge", exact=True).click()
        expect(
            page.get_by_role("heading", name="Who can open this file?", exact=True)
        ).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()


def test_ten_minutes_selects_a_fitting_activity(live_server, tmp_path, pack_data):
    pack_data["node"][0]["minutes"] = 30
    pack_data["node"][2]["minutes"] = 10
    db = Database(tmp_path / "server")
    Tracker(db).install_pack(dump_toml(pack_data))
    db.close()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page.goto(live_server)
        expect(page.locator(".next-card h2")).to_have_text("First task")
        page.get_by_role("button", name="10 min", exact=True).click()
        expect(page.locator(".time-fit-card h2")).to_have_text("Small task")
        assert (
            int(page.locator(".time-fit-card").get_attribute("data-suggested-minutes"))
            <= 10
        )
        # Finishing the short track task promotes genuine short practice next.
        page.request.post(
            live_server + "/api/nodes/test-pack:small/mark", data={"status": "done"}
        )
        page.get_by_role("button", name="10 min", exact=True).click()
        expect(page.locator(".time-fit-card h2")).not_to_have_text("Small task")
        assert (
            int(page.locator(".time-fit-card").get_attribute("data-suggested-minutes"))
            <= 10
        )
        expect(page.locator(".time-fit-card")).to_contain_text("30 minutes")
        card = page.locator(".time-fit-card").bounding_box()
        art = page.locator(".time-fit-card .challenge-art").bounding_box()
        label = page.locator(".time-fit-card > .eyebrow").bounding_box()
        assert (
            art["x"] >= card["x"]
            and art["x"] + art["width"] <= card["x"] + card["width"]
        )
        assert label["width"] < card["width"] * 0.8
        capture(page, "today-ten-minutes")
        page.get_by_role("button", name="Any time", exact=True).click()
        expect(page.locator(".next-card h2")).to_have_text("First task")

        # No fitting option is an explicit empty state, never a longer task.
        def no_fit(route):
            response = route.fetch()
            data = response.json()
            data["practice"] = {"activities": []}
            data["quick_win"] = None
            data["checkpoint"] = None
            route.fulfill(response=response, json=data)

        page.route("**/api/me?minutes=10", no_fit)
        page.route(
            "**/api/playground/recommendations?kind=&minutes=10",
            lambda route: route.fulfill(json={"activities": []}),
        )
        page.get_by_role("button", name="10 min", exact=True).click()
        expect(page.locator(".time-fit-card h2")).to_have_text(
            "No ready task fits this time."
        )
        expect(
            page.locator(".time-fit-card").get_by_role(
                "button", name="Choose more time"
            )
        ).to_be_visible()
        browser.close()


@pytest.mark.parametrize("width", [320, 390, 768, 1440, 1920])
def test_shared_feedback_and_page_geometry(live_server, width):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 1000}, reduced_motion="reduce"
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for route in [
            "today",
            "path",
            "stats",
            "more",
            "docs/timers",
            "playground/quick",
            "playground/challenges",
            "playground/free",
            "playground/history",
            "profile",
        ]:
            page.goto(live_server + "/#" + route)
            expect(page.locator("#route-progress")).not_to_be_visible()
            expect(page.locator(".app-loader")).not_to_be_visible()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), route
            accessibility(page)
            if width >= 1440:
                expect(page.locator(".context-rail")).to_be_visible()
                expect(page.locator(".context-rail h2").first).to_be_visible()
                primary = page.locator(".workspace-primary").bounding_box()
                rail = page.locator(".context-rail").bounding_box()
                assert primary["x"] + primary["width"] < rail["x"], route
                if width == 1920:
                    capture(page, "layout-" + route.replace("/", "-"))
        page.get_by_label("Timezone", exact=True).fill("Asia/Kolkata")
        page.get_by_role("button", name="Save timezone", exact=True).click()
        expect(page.locator("#notice")).to_have_attribute("data-feedback", "success")
        expect(page.locator(".notice-detail")).to_contain_text("Timezone saved")
        assert (
            page.locator("#notice").evaluate(
                "el => el.getAnimations({subtree:true}).length"
            )
            == 0
        )
        capture(page, f"notice-success-{width}")
        page.get_by_label("Timezone", exact=True).fill("Invalid/Nowhere")
        page.get_by_role("button", name="Save timezone", exact=True).click()
        expect(page.locator("#notice")).to_have_attribute("role", "alert")
        expect(page.locator("#notice")).to_have_attribute("data-feedback", "error")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()


def test_older_motion_script_cannot_break_walkthrough(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route(
            "**/effects.js*",
            lambda route: route.fulfill(
                content_type="application/javascript",
                body="window.AscendMotion = {enter() {}, leave() {}};",
            ),
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        run = page.request.post(
            live_server + "/api/playground/activities/example-access/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + run["id"])
        page.get_by_role("button", name="Next step", exact=True).click()
        expect(page.get_by_role("heading", name="Follow one request")).to_be_visible()
        page.get_by_role("button", name="No", exact=True).click()
        expect(page.locator(".pg-prediction-feedback")).to_have_attribute(
            "data-feedback", "success"
        )
        page.get_by_role("button", name="Next step", exact=True).click()
        page.get_by_role("button", name="Finish walkthrough", exact=True).click()
        expect(page.locator(".pg-takeaway h2")).to_be_focused()
        expect(page.locator('#notice[data-kind="error"]')).not_to_be_visible()
        assert not errors
        browser.close()
