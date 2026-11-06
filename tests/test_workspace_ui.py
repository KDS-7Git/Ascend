"""Production workspace surfaces and recovery of overlapping Playground saves."""

import base64
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


def _check_sliding_selection(page, group, selected, before):
    assert before is not None
    marker = group.locator(".selection-indicator")
    positions = marker.evaluate("""async e => {
        const moving = () => e.getAnimations().find(a => a.transitionProperty === 'transform');
        for (let i = 0; i < 30 && !moving(); i++)
            await new Promise(requestAnimationFrame);
        const animation = moving();
        if (!animation) throw new Error('Selection did not slide');
        const frames = animation.effect.getKeyframes();
        const from = new DOMMatrix(frames[0].transform), to = new DOMMatrix(frames.at(-1).transform);
        e.getAnimations().forEach(a => {
            a.pause(); a.currentTime = a.effect.getComputedTiming().duration / 2;
        });
        const middle = new DOMMatrix(getComputedStyle(e).transform);
        return {from:{x:from.m41, y:from.m42}, to:{x:to.m41, y:to.m42}, middle:{x:middle.m41, y:middle.m42}};
    }""")
    start, middle, destination = positions["from"], positions["middle"], positions["to"]
    axis = max(("x", "y"), key=lambda name: abs(destination[name] - start[name]))
    assert (
        min(start[axis], destination[axis])
        < middle[axis]
        < max(start[axis], destination[axis])
    ), positions
    marker.evaluate("e => e.getAnimations().forEach(a => a.finish())")
    after, destination = marker.evaluate(
        "(marker, selected) => [marker.getBoundingClientRect().toJSON(), selected.getBoundingClientRect().toJSON()]",
        selected.element_handle(),
    )
    for name in ("x", "y", "width", "height"):
        assert abs(after[name] - destination[name]) < 1, (after, destination)


@pytest.mark.parametrize("width,theme", [(1440, "light"), (390, "dark")])
def test_navigation_selection_slides_retargets_and_honors_motion(
    live_server, width, theme
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})
        page.add_init_script(f"localStorage.setItem('ascend-theme', '{theme}')")
        page.goto(live_server + "/app")
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        nav = page.locator(".primary-nav")
        marker = nav.locator(".selection-indicator")
        before = marker.bounding_box()
        selected = nav.get_by_role("button", name="Playground", exact=True)
        selected.click()
        expect(selected).to_have_attribute("aria-current", "page")
        _check_sliding_selection(page, nav, selected, before)
        nav.get_by_role("button", name="Stats", exact=True).click()
        nav.get_by_role("button", name="Path", exact=True).click()
        selected = nav.locator("[aria-current='page']")
        expect(selected).to_have_text("Path")
        page.wait_for_function("""() => {
            const a = document.querySelector('.primary-nav .selection-indicator').getBoundingClientRect();
            const b = document.querySelector('.primary-nav [aria-current]').getBoundingClientRect();
            return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1;
        }""")
        page.emulate_media(reduced_motion="reduce")
        nav.get_by_role("button", name="Today", exact=True).click()
        expect(page.locator("html")).to_have_attribute("data-motion", "off")
        page.wait_for_function("""() => {
            const marker = document.querySelector('.primary-nav .selection-indicator');
            const target = document.querySelector('.primary-nav [aria-current]');
            const a = marker.getBoundingClientRect(), b = target.getBoundingClientRect();
            return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1
                && marker.getAnimations().length === 0;
        }""")
        page.emulate_media(forced_colors="active")
        expect(marker).not_to_be_visible()
        expect(nav.get_by_role("button", name="Today", exact=True)).to_have_attribute(
            "aria-current", "page"
        )
        browser.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_time_and_playground_selections_slide_and_resize(live_server, width):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1000})
        page.goto(live_server + "/app")
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        times = page.get_by_role("group", name="Time available")
        before = times.locator(".selection-indicator").bounding_box()
        selected = times.get_by_role("button", name="30 min", exact=True)
        selected.click()
        _check_sliding_selection(page, times, selected, before)
        page.get_by_role("button", name="Playground", exact=True).click()
        _finish_motion(page)
        tabs = page.get_by_role("navigation", name="Playground sections")
        before = tabs.locator(".selection-indicator").bounding_box()
        selected = tabs.get_by_role("link", name="Saved work & history", exact=True)
        selected.click()
        _check_sliding_selection(page, tabs, selected, before)
        page.set_viewport_size(
            {"width": 390 if width == 1440 else 1440, "height": 1000}
        )
        page.wait_for_function("""() => {
            const marker = document.querySelector('.playground-tabs .selection-indicator');
            const target = document.querySelector('.playground-tabs [aria-current]');
            const a = marker.getBoundingClientRect(), b = target.getBoundingClientRect();
            return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1
                && Math.abs(a.width - b.width) < 1 && marker.getAnimations().length === 0;
        }""")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()


def test_rebuilt_guide_lab_and_prediction_selections_slide(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(live_server + "/app#docs/getting-started")
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        topics = page.locator("#docs-topics")
        before = topics.locator(".selection-indicator").bounding_box()
        selected = topics.get_by_role("link", name="Timers & XP", exact=True)
        selected.click()
        _check_sliding_selection(page, topics, selected, before)
        page.goto(live_server + "/app#lab/labtainers-network-basics")
        expect(page.get_by_role("navigation", name="Lab exercises")).to_be_visible()
        _finish_motion(page)
        labs = page.get_by_role("navigation", name="Lab exercises")
        before = labs.locator(".selection-indicator").bounding_box()
        selected = labs.get_by_role("link").nth(1)
        selected.click()
        expect(labs.get_by_role("link").nth(1)).to_have_attribute(
            "aria-current", "page"
        )
        _check_sliding_selection(page, labs, labs.get_by_role("link").nth(1), before)
        response = page.request.post(
            live_server + "/api/playground/activities/example-integrity/start", data={}
        )
        assert response.ok
        run = response.json()
        response = page.request.post(
            live_server + f"/api/playground/runs/{run['id']}/tour", data={"step": 1}
        )
        assert response.ok
        page.goto(live_server + f"/app#activity/{run['id']}")
        choices = page.locator(".pg-prediction")
        expect(choices).to_be_visible()
        _finish_motion(page)
        choices.get_by_role("button").first.click()
        expect(choices.locator(".selection-indicator")).to_be_visible()
        _finish_motion(page)
        before = choices.locator(".selection-indicator").bounding_box()
        selected = choices.get_by_role("button").nth(1)
        selected.click()
        _check_sliding_selection(page, choices, selected, before)
        browser.close()


def test_pack_dropdown_and_decision_selections_slide_independently(
    live_server, pack_data
):
    from ascend.engine.packs import dump_toml

    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "access-policy"}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        response = page.request.post(
            live_server + "/api/packs",
            multipart={
                "file": {
                    "name": "test.toml",
                    "mimeType": "text/plain",
                    "buffer": dump_toml(pack_data).encode(),
                }
            },
        )
        assert response.ok
        page.goto(live_server + "/app#more")
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        page.get_by_text("Import a pack", exact=True).click()
        field = page.get_by_label("Install a community pack by ID", exact=True)
        field.fill("devops")
        dropdown = page.get_by_role("listbox", name="Available community packs")
        field.press("ArrowDown")
        expect(dropdown.locator(".selection-indicator")).to_be_visible()
        _finish_motion(page)
        before = dropdown.locator(".selection-indicator").bounding_box()
        field.press("ArrowDown")
        _check_sliding_selection(
            page, dropdown, dropdown.get_by_role("option", selected=True), before
        )
        field.press("Escape")
        page.get_by_role("button", name="Today", exact=True).click()
        page.locator(".next-card").get_by_role("button", name="Open challenge").click()
        page.get_by_role("button", name="Start verified exercise").click()
        choices = page.get_by_role("group", name="Request r1", exact=True).locator(
            ".decision-choices"
        )
        choices.get_by_role("radio", name="Allow", exact=True).check()
        expect(choices.locator(".selection-indicator")).to_be_visible()
        _finish_motion(page)
        before = choices.locator(".selection-indicator").bounding_box()
        choices.get_by_role("radio", name="Deny", exact=True).check()
        _check_sliding_selection(
            page, choices, choices.locator(".decision-choice").nth(1), before
        )
        page.get_by_role("group", name="Request r2", exact=True).get_by_role(
            "radio", name="Allow", exact=True
        ).check()
        expect(choices.get_by_role("radio", name="Deny", exact=True)).to_be_checked()
        marker_box, selected_box = choices.locator(".selection-indicator").evaluate(
            "(marker, selected) => [marker.getBoundingClientRect().toJSON(), selected.getBoundingClientRect().toJSON()]",
            choices.locator(".decision-choice").nth(1).element_handle(),
        )
        for name in ("x", "y", "width", "height"):
            assert abs(marker_box[name] - selected_box[name]) < 1
        browser.close()


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
        page.goto(live_server + "/app")
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
            const paper = getComputedStyle(card);
            const value = (style, name) => parseFloat(style.getPropertyValue(name));
            if (value(paper, '--paper-grid-size-x') !== size
                || value(paper, '--paper-grid-size-y') !== size
                || Math.abs(bounds.left + card.clientLeft + value(paper, '--paper-grid-x')) > .05
                || Math.abs(bounds.top + card.clientTop + value(paper, '--paper-grid-y')) > .05) return false;
            const layers = [...document.querySelectorAll('.hover-light.pointer-present')];
            return layers.length === 2 && layers.every(layer => {
                const rect = layer.getBoundingClientRect();
                const grid = getComputedStyle(layer);
                const cell = getComputedStyle(layer, '::after');
                const near = (a, b) => Math.abs(a - b) < .05;
                return value(grid, '--grid-size-x') === size && value(grid, '--grid-size-y') === size
                    && near(rect.left + value(grid, '--grid-offset-x'), 0)
                    && near(rect.top + value(grid, '--grid-offset-y'), 0)
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
@pytest.mark.parametrize("pixel_ratio", [1, 1.25])
def test_hover_grid_renders_both_axes_during_fractional_card_movement(
    live_server, theme, pixel_ratio
):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=pixel_ratio,
            reduced_motion="no-preference",
        )
        page.add_init_script(f"localStorage.setItem('ascend-theme', '{theme}')")
        page.goto(live_server + "/app")
        expect(page.locator("#app-loader")).not_to_be_visible()
        _finish_motion(page)
        card = page.locator(".next-card")
        # Isolate the printed lines from text, art and the selected-cell border.
        page.evaluate("""() => {
            const sheet = [...document.styleSheets].at(-1);
            sheet.insertRule('.next-card > :not(.hover-light) { visibility:hidden; }');
            sheet.insertRule('.hover-light::after { display:none; }');
        }""")
        for transform in ["none", "translate(.375px, .625px) scale(.985)"]:
            card.evaluate("(card, value) => card.style.transform = value", transform)
            _finish_motion(page)
            box = card.bounding_box()
            point = {"x": box["x"] + box["width"] / 2, "y": box["y"] + 155}
            page.mouse.move(point["x"], point["y"])
            highlight = card.locator(".hover-light")
            expect(highlight).to_have_css("opacity", "1")
            _finish_motion(page)
            highlight.evaluate(
                "e => { e.style.transition = 'none'; e.style.opacity = '0'; }"
            )
            before = base64.b64encode(page.screenshot(scale="css")).decode()
            highlight.evaluate("e => e.style.opacity = '1'")
            after = base64.b64encode(page.screenshot(scale="css")).decode()
            strength = page.evaluate(
                """async ({before, after, point}) => {
                    const pixels = async encoded => {
                        const image = new Image();
                        image.src = 'data:image/png;base64,' + encoded;
                        await image.decode();
                        const canvas = document.createElement('canvas');
                        canvas.width = image.width; canvas.height = image.height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(image, 0, 0);
                        return {data:ctx.getImageData(0, 0, canvas.width, canvas.height).data,
                            width:canvas.width};
                    };
                    const [off, on] = await Promise.all([pixels(before), pixels(after)]);
                    const delta = (x, y) => {
                        const index = (Math.round(y) * on.width + Math.round(x)) * 4;
                        return Math.max(...[0, 1, 2].map(channel =>
                            Math.abs(on.data[index + channel] - off.data[index + channel])));
                    };
                    const size = parseFloat(getComputedStyle(document.documentElement)
                        .getPropertyValue('--workspace-grid-size'));
                    const x = Math.floor(point.x / size) * size;
                    const y = Math.floor(point.y / size) * size;
                    const strength = vertical => [5, 11, 17, 23].reduce((sum, offset) =>
                        sum + Math.max(...[-1, 0, 1, 2].map(edge => vertical
                            ? delta(x + edge, y + offset) : delta(x + offset, y + edge))), 0) / 4;
                    return {vertical:strength(true), horizontal:strength(false)};
                }""",
                {"before": before, "after": after, "point": point},
            )
            assert strength["vertical"] >= 10, (transform, strength)
            assert strength["horizontal"] >= 10, (transform, strength)
            ratio = strength["vertical"] / strength["horizontal"]
            assert 0.75 <= ratio <= 1.33, (transform, strength)
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
            page.goto(live_server + "/app#" + route)
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
        page.goto(live_server + "/app#path")
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
        touch_page.goto(live_server + "/app")
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
        page.goto(live_server + "/app")
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
        page.goto(live_server + "/app#activity/" + run["id"])
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
        page.goto(live_server + "/app#activity/" + workspace["id"])
        page.get_by_role("button", name="Save workspace", exact=True).click()
        expect(page.locator("#playground")).to_be_visible()
        challenge = page.request.post(
            live_server + "/api/playground/activities/copy-check/start",
            data={"deliberate": True},
        ).json()
        page.goto(live_server + "/app#activity/" + workspace["id"])
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
