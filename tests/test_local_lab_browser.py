import pytest
from playwright.sync_api import expect, sync_playwright
from test_integration import live_server as live_server  # noqa: PLC0414


@pytest.mark.parametrize("width", [390, 1440])
def test_compact_catalog_details_deep_links_and_return(live_server, width):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server + "/#playground/labs")
        expect(page.locator(".pg-lab")).to_have_count(15)
        assert page.locator(".pg-lab pre, .pg-lab details").count() == 0
        assert all(
            len(text) < 330 for text in page.locator(".pg-lab").all_text_contents()
        )
        query = page.get_by_label("Search labs", exact=True)
        query.fill("VAmPI")
        expect(page.locator(".pg-lab")).to_have_count(1)
        page.get_by_role("link", name="Open lab", exact=True).click()
        expect(page.get_by_role("heading", name="VAmPI", exact=True)).to_be_visible()
        expect(page.locator('.primary-nav [data-tab="playground"]')).to_have_attribute(
            "aria-current", "page"
        )
        page.get_by_text("Run on your own Linux computer", exact=True).click()
        expect(
            page.locator("#lab pre").filter(
                has_text="ascend local-lab start vampi-ownership"
            )
        ).to_be_visible()
        page.get_by_text("Source, requirements & verification", exact=True).click()
        expect(page.get_by_role("link", name="Upstream repository")).to_have_attribute(
            "href", "https://github.com/erev0s/VAmPI"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.go_back()
        expect(query).to_have_value("VAmPI")
        expect(page.locator(".pg-lab")).to_have_count(1)
        query.fill("Kubernetes Goat")
        page.get_by_role("link", name="Open lab", exact=True).click()
        page.get_by_text("Run on your own Linux computer", exact=True).click()
        expect(
            page.locator("#lab pre").filter(
                has_text="ascend local-lab prepare kubernetes-goat-rbac"
            )
        ).to_be_visible()
        page.get_by_role("link", name="← Back to Linux labs", exact=True).click()
        expect(query).to_have_value("Kubernetes Goat")
        page.goto(live_server + "/#lab/bgp-session-protection")
        expect(page.get_by_role("heading", name="BGP Labs", exact=True)).to_be_visible()
        expect(
            page.get_by_role("navigation", name="Lab exercises").locator(
                '[aria-current="page"]'
            )
        ).to_have_attribute("href", "#lab/bgp-session-protection")
        page.get_by_text("Run on your own Linux computer", exact=True).click()
        expect(
            page.locator("#lab pre").filter(
                has_text="ascend local-lab start bgp-session-protection"
            )
        ).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.reload()
        expect(
            page.get_by_role("heading", name="Your task", exact=True)
        ).to_be_visible()
        page.goto(live_server + "/#lab/not-a-lab")
        expect(page.get_by_role("alert")).to_contain_text("Unknown lab or recipe")
        assert not errors
        browser.close()


def test_catalog_keyboard_empty_filters_and_detail_connection_error(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(live_server + "/#playground/labs")
        query = page.get_by_label("Search labs", exact=True)
        query.fill("VAmPI")
        link = page.get_by_role("link", name="Open lab", exact=True)
        link.focus()
        page.keyboard.press("Enter")
        expect(
            page.get_by_role("heading", name="Your task", exact=True)
        ).to_be_visible()
        page.get_by_role("link", name="← Back to Linux labs", exact=True).click()
        query.fill("no such laboratory")
        expect(
            page.get_by_text("No labs match these filters.", exact=True)
        ).to_be_visible()
        page.route(
            "**/api/hosted-labs/capabilities",
            lambda route: route.fulfill(
                status=503, json={"detail": "Runner unavailable for testing"}
            ),
        )
        page.goto(live_server + "/#lab/linux-audit-discovery")
        expect(
            page.get_by_text("Runner unavailable for testing", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_text("Source, requirements & verification", exact=True)
        ).to_be_visible()
        page.get_by_text("Run on your own Linux computer", exact=True).click()
        expect(
            page.locator("#lab pre").filter(
                has_text="ascend local-lab start linux-audit-discovery"
            )
        ).to_be_visible()
        browser.close()


def test_browser_server_launch_edit_check_resume_and_download(live_server):
    import json
    import time
    from urllib.parse import parse_qs, urlsplit

    state = {"runs": [], "job": None}
    files = {
        "input/evidence.log": "Authored browser fixture",
        "work/answers.json": "{}",
    }
    actions = []

    def runner(route):
        request = route.request
        path = urlsplit(request.url).path
        if path.endswith("/capabilities"):
            route.fulfill(
                json={"configured": True, "recipes": ["linux-audit-discovery"]}
            )
            return
        if request.method == "GET" and path.endswith("/files"):
            name = parse_qs(urlsplit(request.url).query)["name"][0]
            route.fulfill(
                json={
                    "name": name,
                    "content": files[name],
                    "editable": name.startswith("work/")
                    and state["runs"][0]["status"] == "ready",
                }
            )
            return
        if request.method == "POST":
            action = "start" if path.endswith("/runs") else path.rsplit("/", 1)[1]
            body = request.post_data_json
            actions.append((action, body))
            if action == "start":
                state["runs"] = [
                    {
                        "id": "a" * 32,
                        "recipe_id": "linux-audit-discovery",
                        "title": "Read a Linux audit trail",
                        "status": "ready",
                        "expires_at": time.time() + 7200,
                        "files": list(files),
                        "targets": [],
                        "router": False,
                        "result": None,
                        "evidence_label": "Answer checked on server",
                    }
                ]
            run = state["runs"][0]
            result = {}
            if action == "save":
                files[body["name"]] = body["content"]
            if action == "check":
                result = {"status": "pass", "authority": "server-runner", "xp": 0}
                run["result"] = result
            if action in {"stop", "resume", "finish"}:
                run["status"] = {
                    "stop": "stopped",
                    "resume": "ready",
                    "finish": "destroyed",
                }[action]
            state["job"] = {
                "id": str(len(actions)),
                "action": action,
                "run_id": run["id"],
                "status": "complete",
                "result": result,
            }
            route.fulfill(json=state["job"])
            return
        route.fulfill(json=state)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/hosted-labs/**", runner)
        page.goto(live_server + "/#lab/linux-audit-discovery")
        expect(page.locator(".lab-server")).to_contain_text("Run on the server")
        page.get_by_role("button", name="Launch on server", exact=True).click()
        expect(
            page.get_by_role("button", name="Check work", exact=True)
        ).to_be_visible()
        page.get_by_label("Lab file", exact=True).select_option("work/answers.json")
        text = '{"explanation":"My observed comparison and its limitation."}'
        page.get_by_label("File contents", exact=True).fill(text)
        page.get_by_role("button", name="Save file", exact=True).click()
        expect(page.get_by_label("Lab file", exact=True)).to_have_value(
            "work/answers.json"
        )
        expect(page.get_by_label("File contents", exact=True)).to_have_value(text)
        page.get_by_role("button", name="Check work", exact=True).click()
        expect(
            page.locator(".lab-server").get_by_role(
                "heading", name="Checks passed", exact=True
            )
        ).to_be_visible()
        expect(page.locator(".lab-server")).to_contain_text(
            "Answer checked on server: pass"
        )
        expect(page.locator(".lab-server")).to_contain_text(
            "Finish & keep work records this attempt and releases the runtime."
        )
        expect(page.locator("#xp-balance")).to_have_text("0 XP")
        page.get_by_role("button", name="Stop lab", exact=True).click()
        expect(
            page.get_by_role("button", name="Resume lab", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="Resume lab", exact=True).click()
        expect(
            page.get_by_role("button", name="Check work", exact=True)
        ).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role("button", name="Download saved work", exact=True).click()
        from pathlib import Path

        bundle = json.loads(Path(download.value.path()).read_text())
        assert bundle["files"]["work/answers.json"] == text
        page.get_by_role("button", name="Finish & keep work", exact=True).click()
        expect(
            page.get_by_role("button", name="Start a new server lab", exact=True)
        ).to_be_visible()
        assert [action for action, _ in actions] == [
            "start",
            "save",
            "check",
            "stop",
            "resume",
            "finish",
        ]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()
