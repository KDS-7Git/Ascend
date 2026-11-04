"""Production workspace surfaces and recovery of overlapping Playground saves."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_integration import live_server as live_server_fixture

live_server = live_server_fixture


def _finish_motion(page):
    page.evaluate("""async () => {
        await Promise.all(document.getAnimations()
            .filter(a => Number.isFinite(a.effect.getComputedTiming().endTime))
            .map(a => a.finished.catch(() => {})));
    }""")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_mouse_grid_stays_synchronized_and_keeps_controls_usable(
    live_server, theme, tmp_path
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference"
        )
        page.add_init_script(f"localStorage.setItem('ascend-theme', '{theme}')")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server)
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        grid = page.locator(".workspace-hover")
        expect(
            page.locator(".cube-field, .mouse-graphics, .mouse-marker, .mouse-stamp")
        ).to_have_count(0)
        page.mouse.move(900, 115)
        expect(grid).to_have_css("opacity", "1")
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        assert grid.get_attribute("aria-hidden") == "true"
        expect(grid).to_have_css("pointer-events", "none")
        card = page.locator(".next-card")
        card.scroll_into_view_if_needed()
        _finish_motion(page)
        box = card.bounding_box()
        point = {"x": box["x"] + 120, "y": box["y"] + 80}
        page.mouse.move(point["x"], point["y"])
        expect(card.locator(".hover-light")).to_have_css("opacity", "1")
        aligned = """point => {
            const size = parseFloat(getComputedStyle(document.documentElement)
                .getPropertyValue('--workspace-grid-size'));
            const bodySize = getComputedStyle(document.body).backgroundSize.split(',')[0];
            if (bodySize !== size + 'px ' + size + 'px') return false;
            const card = document.querySelector('.next-card');
            const bounds = card.getBoundingClientRect();
            const paper = getComputedStyle(card, '::before');
            if (!paper.backgroundSize.split(',').every(value => value.trim() === size + 'px ' + size + 'px')
                || Math.abs(bounds.left + card.clientLeft + parseFloat(paper.backgroundPositionX)) > .05
                || Math.abs(bounds.top + card.clientTop + parseFloat(paper.backgroundPositionY)) > .05) return false;
            const layers = [...document.querySelectorAll('.hover-light.pointer-present')];
            return layers.length === 2 && layers.every(layer => {
                const rect = layer.getBoundingClientRect();
                const grid = getComputedStyle(layer, '::before');
                const cell = getComputedStyle(layer, '::after');
                const near = (a, b) => Math.abs(a - b) < .05;
                return grid.backgroundSize.split(',').every(value => value.trim() === size + 'px ' + size + 'px')
                    && near(rect.left + parseFloat(grid.backgroundPositionX), 0)
                    && near(rect.top + parseFloat(grid.backgroundPositionY), 0)
                    && near(rect.left + parseFloat(cell.left), Math.floor(point.x / size) * size)
                    && near(rect.top + parseFloat(cell.top), Math.floor(point.y / size) * size);
            });
        }"""
        page.wait_for_function(aligned, arg=point)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_function(aligned, arg=point)
        page.evaluate("window.scrollBy(0, 40)")
        page.wait_for_function(aligned, arg=point)
        page.screenshot(path=tmp_path / f"synchronized-grid-{theme}.png")
        page.get_by_role("button", name="Path", exact=True).click()
        expect(page.locator("#path")).to_be_visible()
        page.get_by_role("button", name="Tracks", exact=True).click()
        page.get_by_role("button", name="Browse learning tracks", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        search = page.get_by_label("Search subjects and roles", exact=True)
        search.click()
        page.keyboard.type("DevOps")
        expect(search).to_be_focused()
        expect(search).to_have_value("DevOps")
        page.get_by_role("button", name="Close dialog", exact=True).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()
        page.mouse.move(-2, -2)
        expect(grid).to_have_css("opacity", "0")
        page.mouse.move(900, 115)
        expect(grid).to_have_css("opacity", "1")
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        expect(grid).to_have_css("opacity", "0")
        page.mouse.move(901, 116)
        expect(grid).to_have_css("opacity", "1")
        page.emulate_media(forced_colors="active", reduced_motion="no-preference")
        expect(grid).not_to_be_visible()
        page.emulate_media(forced_colors="none", reduced_motion="no-preference")
        page.mouse.move(902, 117)
        expect(grid).to_have_css("opacity", "1")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_mouse_movement_shifts_card_art_and_shadows_without_moving_copy(
    live_server, theme
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference"
        )
        page.add_init_script(f"localStorage.setItem('ascend-theme', '{theme}')")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for route, selector, art_selector, copy_selector in (
            ("today", ".next-card", ".ws-companion>svg", "h2"),
            ("today", ".ws-route-card", ".ws-route-icon", ".ws-route-copy"),
            ("playground", ".pg-catalog-card", ".pg-emblem", "button"),
            ("path", ".level-section", ".level-number", ".level-title"),
        ):
            page.goto(live_server + "/#" + route)
            card = page.locator(selector).first
            expect(card).to_be_visible()
            expect(page.locator("#app-loader")).not_to_be_visible()
            _finish_motion(page)
            surface = card.locator(".level-header") if route == "path" else card
            art = card.locator(art_selector).first
            copy = card.locator(copy_selector).first
            surface.scroll_into_view_if_needed()
            page.evaluate(
                "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
            )
            surface.hover(position={"x": 24, "y": 24})
            expect(card).to_have_attribute("data-pointer-motion", "true")
            _finish_motion(page)
            initial_shadow = card.evaluate("e => getComputedStyle(e).boxShadow")
            initial_art = art.evaluate("e => getComputedStyle(e).translate")
            initial_copy = copy.bounding_box()
            bounds = surface.bounding_box()
            page.mouse.move(
                bounds["x"] + bounds["width"] - 24,
                bounds["y"] + bounds["height"] - 24,
                steps=12,
            )
            expect(card).not_to_have_css("box-shadow", initial_shadow)
            expect(art).not_to_have_css("translate", initial_art)
            _finish_motion(page)
            assert copy.bounding_box() == pytest.approx(initial_copy, abs=0.1)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.mouse.move(1, 1)
            expect(page.locator("[data-pointer-motion]")).to_have_count(0)
            _finish_motion(page)
            expect(art).to_have_css("translate", "0px")
        assert not errors
        browser.close()


def test_mouse_movement_resets_for_press_scroll_navigation_and_motion_preferences(
    live_server,
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference"
        )
        page.goto(live_server + "/#path")
        card = page.locator(".level-section").first
        header = card.locator(".level-header")
        expect(header).to_be_visible()
        _finish_motion(page)
        was_open = card.get_attribute("open") is not None
        header.hover(position={"x": 40, "y": 24})
        expect(card).to_have_attribute("data-pointer-motion", "true")
        page.mouse.down()
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        page.mouse.up()
        if was_open:
            expect(card).not_to_have_attribute("open", "")
        else:
            expect(card).to_have_attribute("open", "")
        header.hover(position={"x": 40, "y": 24})
        expect(card).to_have_attribute("data-pointer-motion", "true")
        page.evaluate("location.hash = '#today'")
        expect(page.locator("#today")).to_be_visible()
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        card = page.locator(".next-card")
        _finish_motion(page)
        card.hover(position={"x": 40, "y": 24})
        expect(card).to_have_attribute("data-pointer-motion", "true")
        page.evaluate("window.scrollBy(0, 40)")
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        card.hover(position={"x": 80, "y": 24})
        expect(card).to_have_attribute("data-pointer-motion", "true")
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        expect(page.locator(".workspace-hover")).not_to_be_visible()
        card.hover(position={"x": 80, "y": 24})
        expect(card).to_have_css("transform", "none")
        expect(card.locator(".ws-companion>svg")).to_have_css("translate", "none")
        page.emulate_media(reduced_motion="no-preference")
        expect(page.locator("html")).to_have_attribute("data-motion", "calm")
        _finish_motion(page)
        card.hover(position={"x": 40, "y": 24})
        expect(card).to_have_attribute("data-pointer-motion", "true")
        expect(page.locator(".workspace-hover")).to_be_visible()
        # The same change event used by the Profile control must reset an active card.
        page.locator("#motion-preference").evaluate("""e => {
            e.value = 'off'; e.dispatchEvent(new Event('change', {bubbles:true}));
        }""")
        expect(page.locator("[data-pointer-motion]")).to_have_count(0)
        expect(page.locator(".workspace-hover")).not_to_be_visible()
        card.hover(position={"x": 80, "y": 24})
        expect(card).to_have_css("transform", "none")
        expect(card.locator(".ws-companion>svg")).to_have_css("translate", "none")
        touch = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        touch_page = touch.new_page()
        touch_page.goto(live_server)
        touch_card = touch_page.locator(".next-card")
        expect(touch_card).to_be_visible()
        _finish_motion(touch_page)
        touch_card.dispatch_event(
            "pointermove", {"pointerType": "touch", "clientX": 150, "clientY": 300}
        )
        expect(touch_page.locator("[data-pointer-motion]")).to_have_count(0)
        expect(touch_page.locator(".workspace-hover")).not_to_be_visible()
        expect(touch_page.locator(".mouse-marker, .mouse-stamp")).to_have_count(0)
        assert touch_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


@pytest.mark.parametrize("width", [390, 768, 1440])
def test_tracks_and_profile_keep_readable_panels_in_both_themes(live_server, width):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})
        for pack in ("io-linux-network", "devops-service-foundations"):
            response = page.request.post(
                live_server + "/api/command", data={"argv": ["pack", "install", pack]}
            )
            assert response.ok
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(live_server)
        for theme in ("light", "dark"):
            page.get_by_role("button", name="Open profile", exact=True).click()
            page.get_by_label("Color theme", exact=True).select_option(theme)
            expect(page.locator("html")).to_have_attribute(
                "data-workspace-theme", theme
            )
            for route in ("profile", "more"):
                if route == "more":
                    page.get_by_role("button", name="Tracks", exact=True).click()
                    expect(page.locator("#more")).to_be_visible()
                    expect(page.locator("#pack-list")).to_contain_text("DevOps")
                panels = page.locator(f"#{route} .card.settings:visible")
                assert panels.count() >= 3
                for panel in panels.all():
                    metrics = panel.evaluate("""e => {
                        const s = getComputedStyle(e);
                        return {background:s.backgroundColor, border:parseFloat(s.borderLeftWidth),
                                padding:parseFloat(s.paddingLeft), width:e.clientWidth, content:e.scrollWidth};
                    }""")
                    assert metrics["background"] != "rgba(0, 0, 0, 0)"
                    assert metrics["border"] == 2
                    assert metrics["padding"] >= 18
                    assert metrics["content"] <= metrics["width"] + 1
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                if folder := os.environ.get("ASCEND_UI_CAPTURE_DIR"):
                    path = Path(folder)
                    path.mkdir(parents=True, exist_ok=True)
                    page.screenshot(
                        path=str(path / f"{route}-{theme}-{width}.png"),
                        full_page=True,
                        animations="disabled",
                    )
        assert not errors
        browser.close()


def test_playground_serializes_saves_and_recovers_newer_unsynced_edits(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        run = page.request.post(
            live_server + "/api/playground/activities/policy-workspace/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + run["id"])
        note = page.get_by_label("What did you learn?", exact=True)
        held = []
        requests = []
        save_url = live_server + "/api/playground/runs/" + run["id"] + "/save"

        def delay_first_save(route):
            requests.append(route.request.post_data_json)
            if len(requests) == 1:
                held.append((route, route.fetch()))
                page.locator("html").evaluate("e => e.dataset.saveHeld = 'true'")
            else:
                route.abort("connectionfailed")

        page.route(save_url, delay_first_save)
        note.fill("First comparison saved to the account.")
        page.evaluate("() => { window.firstSave = savePlaygroundDraft(); }")
        expect(page.locator("html")).to_have_attribute("data-save-held", "true")
        later = "Newer comparison stays recoverable when the next save fails."
        note.fill(later)
        page.evaluate("""() => {
            window.secondSave = savePlaygroundDraft().catch(() => {
                document.documentElement.dataset.saveFailed = 'true';
            });
        }""")
        assert len(requests) == 1
        held[0][0].fulfill(response=held[0][1])
        expect(page.locator("html")).to_have_attribute("data-save-failed", "true")
        assert requests[1]["data"]["notes"] == later
        stored = page.request.get(
            live_server + "/api/playground/runs/" + run["id"]
        ).json()
        assert stored["work"]["notes"] == "First comparison saved to the account."
        page.unroute(save_url)
        page.reload()
        expect(note).to_have_value(later)
        page.get_by_role("button", name="Save workspace", exact=True).click()
        expect(page.locator("#playground-content")).to_contain_text("Saved work")
        stored = page.request.get(
            live_server + "/api/playground/runs/" + run["id"]
        ).json()
        assert stored["work"]["notes"] == later
        assert stored["status"] == "saved"
        browser.close()


def test_workspace_copy_confirms_ending_an_active_timed_challenge(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        workspace = page.request.post(
            live_server + "/api/playground/activities/policy-workspace/start", data={}
        ).json()
        page.goto(live_server + "/#activity/" + workspace["id"])
        page.get_by_role("button", name="Save workspace", exact=True).click()
        expect(page.locator("#playground")).to_be_visible()
        challenge = page.request.post(
            live_server + "/api/playground/activities/copy-check/start",
            data={"deliberate": True},
        ).json()
        page.goto(live_server + "/#activity/" + workspace["id"])
        page.get_by_role("button", name="Duplicate workspace", exact=True).click()
        expect(page.get_by_role("dialog")).to_contain_text(
            challenge["activity"]["title"]
        )
        page.get_by_role("button", name="Cancel", exact=True).click()
        route = live_server + "/api/playground/runs/" + challenge["id"]
        assert page.request.get(route).json()["status"] == "active"
        page.get_by_role("button", name="Duplicate workspace", exact=True).click()
        page.get_by_role(
            "button", name="End scored attempt and switch", exact=True
        ).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()
        expect(
            page.get_by_role("button", name="Run experiment", exact=True)
        ).to_be_enabled()
        assert page.request.get(route).json()["status"] == "ended"
        assert not page.url.endswith(workspace["id"])
        browser.close()
