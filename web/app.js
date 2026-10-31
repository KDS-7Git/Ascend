"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const state = {token: sessionStorage.getItem("ascend-token"), minutes: null, overview: null, levels: [], tab: "today"};
let noticeTimer;
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function button(text, action, className = "secondary") { const node = el("button", text, className); node.type = "button"; node.addEventListener("click", () => Promise.resolve().then(action).catch(error => notify(error.message))); return node; }
function notify(message) { const node = $("#notice"); node.textContent = message; node.hidden = false; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => node.hidden = true, 4500); }
async function api(path, body, method = "POST") {
  const headers = {}; if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const options = {headers, cache: "no-store"};
  if (body !== undefined) { options.method = method; if (body instanceof FormData) options.body = body; else { headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); } }
  let response;
  try { response = await fetch(`/api/${path}`, options); } catch { throw new Error("You're offline. Reconnect to save your progress."); }
  if (response.status === 401) { if (!$("#login-dialog").open) $("#login-dialog").showModal(); throw new Error("Sign in to continue."); }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form fields.");
  return data;
}
const command = argv => api("command", {argv});
async function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".screen").forEach(screen => screen.hidden = screen.id !== tab);
  document.querySelectorAll("[data-tab]").forEach(node => { node.classList.toggle("active", node.dataset.tab === tab); if (node.dataset.tab === tab) node.setAttribute("aria-current", "page"); else node.removeAttribute("aria-current"); });
  location.hash = tab;
  if (tab === "path") await renderPath();
  if (tab === "stats") await renderStats();
  if (tab === "more") await renderMore();
}
async function refresh() {
  state.overview = await api("me" + (state.minutes ? `?minutes=${state.minutes}` : ""));
  $("#streak").textContent = state.overview.current_streak;
  const cards = $("#today-cards"); cards.replaceChildren();
  if (state.overview.next) cards.append(nodeCard(state.overview.next, false));
  else {
    const empty = el("div", undefined, "empty"); empty.append(el("h2", state.overview.mission ? "A smaller step, perhaps." : "A place to begin."), el("p", state.overview.mission ? "No open step fits this time. Try another time or split a step from its Path details." : "Choose a pack and start your first mission in More."));
    empty.append(button(state.overview.mission ? "View path" : "Choose a pack", () => switchTab(state.overview.mission ? "path" : "more")));
    cards.append(empty);
  }
  if (state.overview.quick_win) cards.append(nodeCard(state.overview.quick_win, true));
}
function nodeCard(node, quick) {
  const card = el("article", undefined, `card node-card ${quick ? "quick-card" : "next-card"}${node.milestone ? " milestone-hero" : ""}`);
  card.append(el("p", quick ? "QUICK WIN · ANYTIME" : "UP NEXT", "eyebrow"));
  card.append(el("p", `${state.overview.mission?.title || ""}${state.overview.draft ? " · Draft pack" : ""}`, "muted"));
  if (node.milestone) card.append(el("span", "◇ Milestone", "milestone-label"));
  card.append(el("h2", node.title), el("p", node.done_when, "description"), el("span", `~${node.estimate} min`, "pill"));
  card.append(button("Log it", () => openLog(node), "log-button"));
  return card;
}
function openSheet() { const dialog = $("#sheet"); $("#sheet-content").replaceChildren(); if (!dialog.open) dialog.showModal(); return $("#sheet-content"); }
function field(form, name, label, type = "text", value = "") {
  const lbl = el("label", label); lbl.htmlFor = name;
  const input = el(type === "textarea" ? "textarea" : "input"); input.id = name; input.name = name;
  if (type !== "textarea") input.type = type; input.value = value;
  form.append(lbl, input); return input;
}
function openLog(node) {
  const content = openSheet(); const title = el("h2", "One small step, recorded."); title.id = "sheet-title";
  content.append(title, el("p", node.title, "muted"));
  const form = el("form");
  const learned = field(form, "learned", "What I did", "textarea"); learned.required = true; learned.minLength = 20;
  const next = field(form, "next-step", "What's next", "text", state.overview.resume || `Continue with ${node.title}`); next.required = true;
  const details = el("details"); details.append(el("summary", "Add details"));
  const minutes = field(details, "minutes", "Minutes spent", "number"); minutes.min = "1"; minutes.max = "1440";
  const proof = field(details, "proof", "Proof link or file path");
  const checkLabel = el("label", undefined, "check"); const complete = el("input"); complete.type = "checkbox"; complete.id = "complete";
  checkLabel.append(complete, document.createTextNode("Mark as done")); details.append(checkLabel);
  if (node.verify?.type !== "manual") details.append(el("p", "Your verifier will check this when you log.", "muted"));
  form.append(details);
  const error = el("p", "", "error"); error.setAttribute("role", "alert"); error.hidden = true;
  const submit = el("button", "Log"); form.append(error, submit); content.append(form);
  form.addEventListener("submit", async event => {
    event.preventDefault(); submit.disabled = true;
    try {
      const result = await api("entries", {learned: learned.value, next_step: next.value, proof: proof.value || null, minutes: minutes.value ? Number(minutes.value) : null, node_id: `${node.pack_id}:${node.id}`, complete: complete.checked});
      $("#sheet").close(); await refresh();
      if (state.tab === "path") await renderPath();
      notify(result.verification && !result.completed ? `Progress saved. ${result.verification}` : "✓ Your step is saved.");
    } catch (err) { error.textContent = err.message; error.hidden = false; } finally { submit.disabled = false; }
  });
  learned.focus();
}
function showNode(node, level) {
  const content = openSheet(); const title = el("h2", node.title); title.id = "sheet-title";
  content.append(title, el("p", node.done_when));
  const link = el("a", "Open learning resource ↗"); link.href = node.resource; link.target = "_blank"; link.rel = "noopener noreferrer"; content.append(link);
  if (!node.open && node.status === "todo") {
    const missing = node.needs?.length ? `Complete prerequisites: ${node.needs.join(", ")}.` : "Unlocks after the previous main level's milestone.";
    content.append(el("p", missing, "muted"));
  }
  const actions = el("div", undefined, "dialog-actions");
  actions.append(button("Log it", () => openLog(node), ""));
  actions.append(button("Mark done", async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: "done"}); $("#sheet").close(); await refresh(); await renderPath(); }));
  actions.append(button("Skip", async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: "skipped"}); $("#sheet").close(); await refresh(); await renderPath(); }));
  if (node.verify?.type !== "manual") actions.append(button("Check evidence", async () => { const result = await command(["check", `${node.pack_id}:${node.id}`]); notify(result.summary); }));
  if (!level.open) actions.append(button("Unlock level", async () => { await command(["unlock", level.id]); $("#sheet").close(); await refresh(); await renderPath(); }));
  content.append(actions);
  if (node.status === "todo") {
    const details = el("details"); details.append(el("summary", "Split into smaller steps"));
    const parts = field(details, "split-parts", "One concrete step per line", "textarea");
    details.append(button("Save smaller steps", async () => { await command(["split", `${node.pack_id}:${node.id}`, ...parts.value.split("\n").filter(Boolean)]); $("#sheet").close(); await refresh(); await renderPath(); })); content.append(details);
  }
}
async function renderPath() {
  state.levels = await api("levels"); const root = $("#path-content"); root.replaceChildren();
  if (!state.levels.length) { root.append(el("p", "Start a mission in More to see your path.", "muted")); return; }
  const side = state.levels.filter(level => level.lane === "side");
  if (side.length) {
    const anytime = el("section", undefined, "anytime"); anytime.append(el("h2", "Anytime")); const strip = el("div", undefined, "anytime-strip");
    for (const lv of side) for (const node of lv.nodes) strip.append(button(`${node.status === "done" ? "✓ " : ""}${node.title}`, () => showNode(node, lv)));
    anytime.append(strip); root.append(anytime);
  }
  for (const level of state.levels.filter(lv => lv.lane === "main")) {
    const section = el("section", undefined, "level-section"); const header = el("div", undefined, "level-header");
    header.append(el("h2", level.title), el("span", `${level.done}/${level.total} steps · ${level.active_days} active days`, "muted"));
    const progress = el("progress", undefined, "progress"); progress.max = level.total || 1; progress.value = level.done; progress.setAttribute("aria-label", `${level.title} progress`);
    const list = el("div", undefined, "path-nodes");
    for (const node of level.nodes) {
      const status = node.status !== "todo" ? node.status : node.open ? "open" : "locked";
      const item = button("", () => showNode(node, level), `path-node ${status}${node.milestone ? " milestone" : ""}`);
      const shape = el("span", undefined, "node-shape"); shape.append(el("span", status === "done" ? "✓" : status === "skipped" ? "–" : node.milestone ? "◇" : status === "locked" ? "·" : ""));
      shape.setAttribute("aria-hidden", "true"); item.setAttribute("aria-label", `${node.title}, ${status}${node.milestone ? ", milestone" : ""}`);
      item.append(shape, el("span", node.title)); list.append(item);
    }
    section.append(header, progress, list); root.append(section);
  }
}
async function renderStats() {
  const [stats, days] = await Promise.all([api("stats"), api("heatmap")]); const root = $("#stats-content"); root.replaceChildren();
  const streak = el("section", undefined, "card"); streak.append(el("h2", "Showing up, one day at a time."), el("span", `${stats.current_streak}`, "streak-number"), el("span", ` days · best ${stats.best_streak}`, "muted"), el("p", `${stats.freeze_available} freeze available this week`, "muted"));
  const calendar = el("section", undefined, "card"); calendar.append(el("h2", "Your last 12 weeks")); const heat = el("div", undefined, "heatmap");
  for (const day of days) { const cell = el("div", undefined, `heat-day${day.count ? " logged" : ""}`); cell.title = `${day.day}: ${day.count} entries`; cell.setAttribute("aria-label", cell.title); cell.setAttribute("role", "img"); heat.append(cell); }
  calendar.append(heat);
  const minutes = el("section", undefined, "card"); minutes.append(el("h2", "Time well spent"), el("p", `${stats.minutes_this_week} minutes this week`, "muted")); const chart = el("div", undefined, "weekly-chart");
  const max = Math.max(1, ...stats.weeks.map(week => week.minutes));
  for (const week of stats.weeks) {
    const item = el("div", undefined, "week");
    const bar = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    bar.setAttribute("viewBox", "0 0 40 120"); bar.setAttribute("width", "40"); bar.setAttribute("height", "120");
    bar.setAttribute("role", "img"); bar.setAttribute("aria-label", `${week.week}: ${week.minutes} minutes`);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const height = Math.max(2, week.minutes / max * 118);
    rect.setAttribute("x", "4"); rect.setAttribute("width", "32"); rect.setAttribute("y", String(120-height)); rect.setAttribute("height", String(height)); rect.setAttribute("rx", "5"); rect.setAttribute("fill", "currentColor");
    bar.append(rect); item.append(el("span", `${week.minutes}m`), bar, el("span", week.week.slice(5))); chart.append(item);
  }
  minutes.append(chart); root.append(streak, calendar, minutes);
}
async function renderMore() {
  const [packs, parked, account] = await Promise.all([api("packs"), command(["parked"]), api("account")]);
  $("#mission-name").textContent = state.overview?.mission?.title || "No active mission";
  $("#mission-time").value = state.overview?.mission?.nudge_time || "";
  $("#mission-pack").replaceChildren(...packs.map(pack => { const option = el("option", pack.id); option.value = pack.id; return option; }));
  $("#pack-list").replaceChildren();
  for (const pack of packs) { const row = el("div", undefined, "pack-item"); row.append(el("p", `${pack.id} · ${pack.reviewed ? "reviewed" : "draft / unreviewed"} · ${pack.trusted ? "commands trusted" : "commands untrusted"}`)); row.append(button("Read pack", async () => { const data = await api(`packs/${pack.id}`); const content = openSheet(); const heading = el("h2", data.title); heading.id = "sheet-title"; content.append(heading); for (const node of data.nodes) content.append(el("h3", node.title), el("p", node.done_when)); content.append(button("Mark reviewed", async () => { await command(["pack", "review", pack.id]); $("#sheet").close(); await renderMore(); })); })); $("#pack-list").append(row); }
  $("#parked-list").replaceChildren(...parked.map(idea => { const item = el("li", idea.note); item.append(button("Resolve", async () => { await command(["resolve", String(idea.id)]); await renderMore(); })); return item; }));
  $("#account-info").textContent = `${account.username} · ${location.origin}`;
  $("#account-timezone").value = account.timezone;
  $("#nudge-time").value = account.settings.nudge_time || "21:30";
  $("#nudge-channel").value = account.settings.nudge_channel || "ntfy";
  $("#ntfy-topic").value = account.settings.ntfy_topic || "";
  $("#nudge-enabled").checked = account.settings.nudge_enabled || false;
  $("#logout").hidden = account.auth_mode === "single";
  $("#public-streak").checked = account.settings.public_streak || false;
  $("#public-link").textContent = account.settings.public_streak ? `${location.origin}/api/public/${encodeURIComponent(account.username)}/badge.svg` : "Your streak is private.";
}
document.querySelectorAll("[data-tab]").forEach(node => node.addEventListener("click", () => switchTab(node.dataset.tab).catch(error => notify(error.message))));
$("#streak-link").addEventListener("click", () => switchTab("stats").catch(error => notify(error.message)));
document.querySelectorAll("[data-minutes]").forEach(node => node.addEventListener("click", async () => { state.minutes = node.dataset.minutes || null; document.querySelectorAll("[data-minutes]").forEach(chip => chip.setAttribute("aria-pressed", String(chip === node))); try { await refresh(); } catch (error) { notify(error.message); } }));
$("#sheet .close").addEventListener("click", () => $("#sheet").close());
$("#sheet").addEventListener("click", event => { if (event.target === $("#sheet")) { const box = event.target.getBoundingClientRect(); if (event.clientY < box.top || event.clientX < box.left || event.clientX > box.right) event.target.close(); } });
function handleForm(selector, handler) { $(selector).addEventListener("submit", async event => { event.preventDefault(); try { await handler(event); } catch (error) { notify(error.message); } }); }
handleForm("#search-form", async () => { const results = await api(`search?q=${encodeURIComponent($("#search").value)}`); $("#search-results").replaceChildren(...results.map(entry => { const item = el("article", undefined, "search-result"); item.append(el("p", entry.learned), el("p", `${entry.day} · ${entry.node_id || "Personal note"}`, "muted")); return item; })); if (!results.length) $("#search-results").append(el("p", "No matching notes yet.", "muted")); });
handleForm("#install-form", async () => { await command(["pack", "install", $("#pack-id").value]); await renderMore(); notify("Pack installed. Read it before trusting its checks."); });
$("#pack-upload").addEventListener("change", async event => { if (!event.target.files[0]) return; const data = new FormData(); data.append("file", event.target.files[0]); try { await api("packs", data); await renderMore(); notify("Pack installed."); } catch (error) { notify(error.message); } });
$("#start-mission").addEventListener("click", async () => { try { const args = ["mission", "start", $("#mission-pack").value]; if ($("#mission-time").value) args.push("--nudge-time", $("#mission-time").value); await command(args); await refresh(); await renderMore(); notify("Mission started."); } catch (error) { notify(error.message); } });
for (const action of ["pause", "finish"]) $(`#${action}-mission`).addEventListener("click", async () => { try { await command(["mission", action]); await refresh(); await renderMore(); } catch (error) { notify(error.message); } });
$("#save-mission-time").addEventListener("click", async () => { try { await command(["mission", "nudge-time", $("#mission-time").value || "off"]); await refresh(); notify("Mission reminder saved."); } catch (error) { notify(error.message); } });
handleForm("#reminder-form", async () => { await command(["config", "nudge-time", $("#nudge-time").value]); await command(["config", "nudge-channel", $("#nudge-channel").value]); if ($("#ntfy-topic").value) await command(["config", "ntfy-topic", $("#ntfy-topic").value]); await command(["config", "nudge-enabled", String($("#nudge-enabled").checked)]); notify("Reminders saved."); });
$("#test-nudge").addEventListener("click", async () => { try { const result = await command(["config", "nudge-test"]); notify(result.sent ? "Test reminder sent." : result.reason); } catch (error) { notify(error.message); } });
handleForm("#park-form", async () => { await command(["park", $("#park-note").value]); $("#park-note").value = ""; await renderMore(); });
$("#save-timezone").addEventListener("click", async () => { try { await command(["config", "timezone", $("#account-timezone").value]); await refresh(); notify("Timezone saved."); } catch (error) { notify(error.message); } });
function setTheme(theme) { if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; localStorage.setItem("ascend-theme", theme); }
$("#theme").value = localStorage.getItem("ascend-theme") || "system"; setTheme($("#theme").value);
$("#theme").addEventListener("change", event => setTheme(event.target.value));
$("#logout").addEventListener("click", async () => { try { await api("logout", {}); sessionStorage.removeItem("ascend-token"); state.token = null; location.reload(); } catch (error) { notify(error.message); } });
$("#public-streak").addEventListener("change", async event => { try { await command(["config", "public-streak", String(event.target.checked)]); await renderMore(); } catch (error) { notify(error.message); } });
$("#enable-push").addEventListener("click", async () => {
  try {
    if (!("Notification" in window) || !("PushManager" in window) || !window.isSecureContext) throw new Error("Browser notifications require HTTPS and a supported browser.");
    if (await Notification.requestPermission() !== "granted") throw new Error("Notification permission was not granted.");
    const {public_key} = await api("push/key");
    const raw = atob(public_key.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4-public_key.length%4)%4));
    const key = Uint8Array.from(raw, character => character.charCodeAt(0));
    const worker = await navigator.serviceWorker.ready;
    const subscription = await worker.pushManager.getSubscription() || await worker.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: key});
    await api("push/subscriptions", subscription.toJSON());
    await command(["config", "nudge-channel", "webpush"]);
    $("#nudge-channel").value = "webpush";
    $("#push-status").textContent = "This browser is subscribed. Enable reminders and send a test when ready.";
  } catch (error) { $("#push-status").textContent = error.message; }
});
$("#disable-push").addEventListener("click", async () => {
  try {
    if (!("serviceWorker" in navigator)) throw new Error("This browser does not support notifications.");
    const worker = await navigator.serviceWorker.ready;
    const subscription = await worker.pushManager.getSubscription();
    if (subscription) { await api("push/subscriptions", {endpoint: subscription.endpoint}, "DELETE"); await subscription.unsubscribe(); }
    $("#push-status").textContent = "Notifications are disabled on this browser.";
  } catch (error) { $("#push-status").textContent = error.message; }
});
handleForm("#login-form", async () => { try { const result = await api("login", {username: $("#username").value, password: $("#password").value}); state.token = result.token; sessionStorage.setItem("ascend-token", result.token); $("#password").value = ""; $("#login-dialog").close(); await refresh(); await switchTab(state.tab); } catch (error) { $("#login-error").textContent = error.message; } });
document.addEventListener("keydown", event => { if (event.key.toLowerCase() === "l" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !$("#sheet").open && state.overview?.next) openLog(state.overview.next); });
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
refresh().then(() => switchTab(["today", "path", "stats", "more"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "today")).catch(error => notify(error.message));
