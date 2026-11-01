# Ascend: UI/UX design brief for the web client (PWA)

The original brief below is retained as design history. The owner's subsequent
request for a more motivating interface is implemented and documented in the
[engagement audit](engagement-audit.md), which supersedes the logging-first flow
and visual constraints here while retaining the four-screen structure.

This is a precise design brief for whoever builds `web/` (see `spec-v3-public-release.md` §10 Phase 2). Read it
alongside that file and `hackstreak-spec-v2.md`. It describes exactly what to build and why, not just "make it look
nice" — follow the structure, states and rules below rather than inventing your own IA.

## 0. The one thing this UI must not become

The whole project exists because the owner gets overwhelmed by open-ended choice and loses the thread. A UI that
shows everything at once — all levels, all stats, all settings, on one dashboard — recreates the exact problem this
tool is supposed to solve. **The test for every screen: could someone open this app, in under 3 seconds, see the one
thing they're meant to do right now, and do it in one tap?** If a screen fails that test, it's wrong, no matter how
complete or impressive it looks.

Second constraint, just as important: **don't build dark patterns.** No fake urgency ("only 2 hours left!"), no
guilt-laden copy ("You're letting your streak die!"), no manipulative streak-loss modals, no infinite-scroll feeds.
The owner has already noticed these mechanics pull on them harder than they'd like. Design for a satisfying, honest
"I did the thing" feeling — not for compulsive reopening.

## 1. Information architecture: 4 screens, bottom nav, nothing deeper than 2 taps

```
[ Today ]   [ Path ]   [ Stats ]   [ More ]
```

Four tabs, fixed bottom nav bar on mobile (thumb-reachable), persistent left rail on desktop/tablet widths. Four, not
five or six — every extra top-level destination is a decision the owner has to filter out before reaching the thing
they came for. Anything that doesn't earn a tab (settings, pack management, parked ideas, account) lives inside
**More**, not bolted onto the nav bar.

- **Today** — the default screen on open. One primary action. This is 80% of real usage.
- **Path** — the visual level map (the Duolingo-inspired piece), browsed, not acted from by default.
- **Stats** — streak, heatmap, minutes, search. Looked at, not acted on.
- **More** — settings, missions/packs, nudges, account. Everything infrequent.

## 2. Today screen (the one that matters most)

Single-column, generous vertical spacing, nothing below the fold on a phone except what's described here.

1. **Header strip** (small, top, never dominant): streak number + a small flame/leaf glyph, tappable → jumps to
   Stats. It must read as *information*, not as a warning light. No red, no countdown, no "at risk" badge glowing
   here — "at risk" framing is reserved for the nudge notification itself (spec v2 §11b), not for a screen the owner
   opens voluntarily. Being reminded gently when prompted is fine; being alarmed every time they check in is not.
2. **Time-available chips**, directly under the header: `10 min` `30 min` `2 hr+` `Surprise me`. Tapping one filters
   what "Next" shows below (implements `ascend <minutes>` from the spec) — this is how a busy day becomes a
   zero-decision day, since the owner never has to mentally estimate what fits.
3. **The Next card** — the hero of the screen, large, filled with the accent color, rounded corners, generous
   padding:
   - Mission name, small, muted, above the title (context, not the focus)
   - Node title, large, bold
   - One line: the `done_when` sentence, in the owner's actual words, not a category label
   - A size pill (`~20 min`, derived from S/M/L, not the raw letter — minutes mean something, a letter doesn't)
   - A milestone node gets a distinct visual treatment here too (a small star/diamond accent, a slightly different
     card border) so "this one's the real test" is legible before they even tap in
   - One primary button: **Log it**. Not "Start," not "Begin session" — the action that matters is recording real
     work, and the button name should say exactly that.
4. **The Quick win card**, directly below, visually secondary: smaller, outlined (not filled), lower visual weight.
   Same shape (title, one line, size pill, Log it button) but unmistakably "the alternate," not "the second
   mandatory task." This is the side-lane node (e.g. the next Bandit level). On a day the owner only has 10 minutes
   and no energy for the main path, this is what they tap, with zero guilt implied by its smaller presence.
5. Nothing else on this screen. No activity feed, no "other packs you could start," no ads for features. If there's
   a parked idea or a pending nudge-config issue, it does not appear here — it waits in More.

### Log-it flow (bottom sheet, not a new page)

Tapping "Log it" slides up a sheet over the current screen (the owner never loses their place):

- Two required fields only: **"What I did"** (free text, the `learned` field) and **"What's next"** (`next_step`),
  the latter pre-filled with a sensible default (the next node's title) so it's editable, not blank — reduces the
  blank-page stall this owner has described elsewhere.
- A collapsed **"Add details"** disclosure (closed by default) reveals: minutes spent, a proof link/file path, and —
  only if the node has a verifier — a "Mark as done" toggle with the verifier's pass/fail shown inline.
- One confirm button: **Log**. On success, the sheet closes with a brief, quiet confirmation (a checkmark that
  animates in and fades, under 400ms, not a confetti burst or a modal the owner must dismiss) and the streak number
  in the header ticks up. Small and satisfying, not a spectacle.

## 3. Path screen (the Duolingo-inspired piece — adapted, not copied)

Duolingo's winding horizontal path is built for one fixed curriculum. This app has editable, user-authored levels of
varying length, so: **a simple vertical path, grouped by level, scrolling top to bottom.** Easier to build, easier to
scan, and it still delivers the thing that actually matters from Duolingo's design — visible structure and
visible progress — without copying its visual identity.

- Levels render as sections in pack order, each with a header: level title, a thin progress bar, and `3/8 steps`.
  A level also shows its active-days count in small muted text (the day-wise tracking from the spec), e.g. `5 active
  days`.
- Within a level, nodes sit on a vertical line as circles:
  - **Locked** — grey outline, a small padlock glyph, muted title text. Tapping shows a brief tooltip: "Unlocks
    after [previous level]." Locked must look *dormant*, not *forbidden* — no red, no X mark. The owner has
    described real shame around unfinished things; a locked node should read as "not yet," never as a failure.
  - **Open** — accent-colored outline, filled title text, tappable.
  - **Done** — filled solid in the accent color with a checkmark. Satisfying, final, no further affordance.
  - **Milestone** — a distinctly different shape, not just a bigger circle: a diamond or hexagon rather than a
    circle (reuse whatever your icon set already has — the point is unmistakable silhouette, not elaborate art), in
    a second accent color used nowhere else in the UI. This node must be visually "the boss level" at a glance,
    because the spec gates the whole level's progress on it — the owner should immediately understand that this one
    node is different in kind, not just in size.
- The **side lane** (quick-win material like Bandit) is NOT mixed into this vertical list. It renders as its own
  small horizontal scrollable strip pinned above the main path, visually separated by a label ("Anytime") and a
  lighter background tint — making clear it's always available and never gates anything.
- Tapping any open or done node opens a small detail sheet (same sheet component as Log-it): title, `done_when`,
  resource link (opens externally), verify status if any, and Log it / Mark done / Skip actions.

## 4. Stats screen

Three stacked sections, each a card, no dashboard-grid of a dozen tiles:

1. **Streak block**: current streak (large number), best streak (small, beside it), freeze availability as a single
   quiet line ("1 freeze available this week"), not an icon-heavy meter.
2. **Heatmap**: a standard GitHub-style calendar heatmap, 12 weeks, in the accent color at varying opacity (not a
   second unrelated color scale) so it reads as "this app," not a borrowed component.
3. **Minutes**: a simple weekly bar chart of logged minutes (the field the earlier audit found was captured but
   never shown) — four to eight bars, nothing fancier.

A **search bar** sits above all three: "Search your notes." Results are a plain reverse-chronological list of past
`learned` lines, each showing its date and which node it was logged against. This is the one place the owner's
accumulated months of real notes become useful again, so don't bury it in More.

## 5. More screen

A plain, grouped settings list — this screen is allowed to look like a conventional settings page, because it's
visited rarely and clarity beats cleverness here:

- **Active mission** (switch / view others)
- **Packs** (installed list, install new, the lint/review state of each)
- **Reminders** (nudge time, channel: ntfy/Telegram/desktop, per-mission override, a "send test" button)
- **Appearance** (light / dark / system — see §6)
- **Parked ideas** (the rabbit-hole list — reviewed here, deliberately out of the way of Today)
- **Account / Server** (only shown in server mode: who you're logged in as, which server)

## 6. Visual language (concrete values, not vibes)

- **Palette**: one calm accent, not a primary-color riot. A desaturated teal or forest green (`#2F6F5E`-ish range)
  reads as "growth," fits the name "Ascend," and is calmer than Duolingo's saturated greens/golds. Pair it with a
  near-white (`#FAFAF8`) background in light mode and a near-black, not pure-black (`#15181B`-ish) in dark mode — pure
  black against bright accent colors reads harsher than it needs to. The milestone accent (used ONLY for milestone
  nodes and nowhere else) should be a warm, muted amber, not neon gold — special, not loud.
- **Type**: one typeface, a standard humanist sans (system font stack is fine — this is a utility app, not a brand
  showcase). Clear hierarchy: large/bold for the Next card title and the streak number, everything else restrained.
  Don't use more than 3 font sizes on any single screen.
- **Spacing**: generous, not cramped — this is an anti-clutter requirement, not a cosmetic one. Minimum 16px side
  gutters on mobile, at least 12px between stacked cards, comfortable 44px+ tap targets throughout (this also
  happens to satisfy basic accessibility tap-target guidance for free — do this by default, it costs nothing, even
  though a full accessibility pass is out of scope per the earlier audit).
- **Motion**: small and purposeful only — the Log-it confirmation checkmark, a progress bar filling, a node flipping
  from open to done. Nothing animates to grab attention; nothing loops; no celebratory full-screen takeovers.
- **Corners/elevation**: soft rounded corners (12-16px) on cards, one subtle shadow level, no heavy skeuomorphism and
  no flat-and-bordered brutalism either — aim for the restrained-card look of a well-made note-taking app (closer to
  Trilium's calm utility than a marketing landing page).

## 7. Responsive behavior: three real breakpoints, not "mobile app that also loads on desktop"

This is opened from a phone home screen some days and a laptop browser other days — design both as genuine primary
use, not one real target and one that merely "doesn't break." Same 4-screen IA throughout; what changes is layout
density and nav placement, not the structure.

**Mobile (< 640px)**
- Bottom nav bar (§1), single column, full-width cards, Log-it as a bottom sheet.
- Side gutters 16px minimum (§6).

**Tablet (640–1024px)**
- Left nav rail replaces the bottom bar (icon + label each).
- Today: Next and Quick-win cards sit side by side, not stacked — there's room for both without crowding.
- Log-it opens as a centered modal instead of a bottom sheet.

**Desktop (1024px+)**
- Left nav rail, same as tablet.
- Content area has a max width (roughly 920–1000px) and stays centered. Do not stretch cards edge-to-edge on a wide
  monitor — extra width becomes margin, not bigger cards. A single card stretched wall-to-wall on a 27" monitor
  reads worse, not better.
- Today: Next and Quick-win side by side, time-available chips above both.
- Path: keep the vertical level path in the same centered max-width column as everything else — do not turn it into
  a multi-column grid of levels. A taller, narrower scroll reads better than a wide, shallow one for a sequential
  roadmap; resist the obvious "I have width, let me use a grid" instinct here specifically.
- Add hover states on interactive elements (cards, nodes, buttons) — a subtle elevation or border-color shift is
  enough, nothing elaborate; desktop has a pointer, so static elements shouldn't feel inert.
- Worth including, nearly free: a keyboard shortcut (e.g. `L`) that opens Log-it for the current Next step directly,
  for a user already at a keyboard. Optional, not load-bearing.

Standard CSS (flex/grid + media queries, or a utility framework's responsive classes) covers all of this — no
JavaScript-driven layout switching needed.

## 8. What this brief deliberately leaves out

No onboarding-flow screens, no animated empty-state illustrations, no custom icon set (use a standard open icon
library — Lucide or Feather are both fine, pick one and use it consistently), no marketing/landing page. Those are
real design work but not what makes this tool work day to day, and building them now would be the same mistake as
over-building the backend before Phase 1 proved itself — effort spent on polish before the core loop is in daily use.

## 9. Text to hand the coding agent

> Build `web/` as described in `ui-ux-spec.md` precisely — the screen structure (Today/Path/Stats/More), the Next
> and Quick-win card distinction, the vertical level path with locked/open/done/milestone node states, the Log-it
> bottom sheet, and the color/spacing/motion values given are not suggestions to riff on, they are the spec. Where
> something is genuinely unspecified (icon choice, exact shadow values), use your own judgment within the stated
> constraints (calm palette, generous spacing, restrained motion) rather than defaulting to a generic admin-dashboard
> look. Do not add screens, nav items, or dashboard widgets beyond what's listed. Ask before deviating from the
> information architecture in section 1.
