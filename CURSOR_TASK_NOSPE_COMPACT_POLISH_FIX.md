# Cursor Task: Fix Bad Compact UI — Balanced One-Screen Scanner Utility

Workspace: `/root/nospe`

Use Claude Opus high/xhigh only. Do NOT use max. Do NOT use fast mode.
Follow the installed Impeccable skill/design discipline: critique honestly, then polish. This is a visual/UX fix task.

## Context

The current ultra-compact UI technically fits without scrolling, but the user correctly says it looks bad:
- Controls are crammed together at the top.
- Half the app is empty white space.
- It looks unfinished, not intentionally minimal.
- Scan button is visually disconnected from the form.
- Paperless / skew / mirror pills look too prominent and weird.
- There is no real scanner-app feeling.

Do NOT respond by making it spacious dashboard again. Keep one-screen, compact, utility-first. But make it balanced and polished.

## What is bad in the current screenshot

Fix these concrete issues:
1. **Top cramped / bottom empty**
   - Controls currently occupy a tiny strip at top while a massive blank area sits below.
   - Either reduce app/container height or use the middle meaningfully.
   - Do not leave giant dead whitespace.

2. **Scan button too far away**
   - Move the primary scan action closer to the form/preview/status area.
   - It should feel connected to the workflow.

3. **No visual scanner concept**
   - Add a compact, useful middle area such as:
     - mini document preview/drop area,
     - “Bereit” status panel,
     - last scan mini-result,
     - or a paper/document illustration.
   - Keep it small, not dashboard-like.

4. **Controls look like generic HTML form**
   - Improve segmented controls visually.
   - Improve active states, focus states, hover states.
   - Make toggles look like toggles, not giant action pills.

5. **Paperless/Skew/Mirror too prominent**
   - Make these compact option chips/toggles.
   - They must not compete with the scan button.

6. **Path dominates too much**
   - Show a shortened path, e.g. `…\Documents\Scans`, with a folder icon/button.
   - Full path can remain in input title/tooltip or settings.

7. **Technical footer too nerdy**
   - Replace `Backend online v0.1.0` style with a subtle status like `Bereit · Backend online`.
   - Version can be less prominent or in settings.

8. **Header clutter**
   - Keep header minimal: Nospe, small device chip, refresh icon, settings icon.
   - Make it feel intentional.

## Target design

A polished compact light-mode scanner utility window:
- width: around 430–480px
- height: should match content naturally, or use middle preview/status intentionally
- no scrolling at 1280×720
- balanced vertical rhythm: not cramped, not empty
- main controls visible without scrolling:
  - filename
  - folder select/path
  - S/W / Grau / Farbe
  - rotate 0/90/180/270
  - horizontal mirror
  - skew correction
  - optional Paperless send
  - scan button
- scanner small in header
- profile in settings
- settings via gear icon only

## Suggested structure

Header row, compact.

Main:
- two compact input rows:
  - Dateiname
  - Zielordner short path + folder button
- one tidy two-column-ish controls block:
  - Modus segmented
  - Drehung segmented
- one compact option row:
  - Spiegeln toggle/chip
  - Schräglage toggle/chip
  - Paperless toggle/chip
- small central “document/status” panel:
  - paper icon/preview rectangle
  - status text: `Bereit zum Scannen`
  - maybe selected mode summary: `S/W · 300 dpi · PDF`
- action row directly beneath that:
  - optional small `Vorschau`
  - primary `Scannen`

Settings drawer:
- Leave existing settings drawer behavior intact.
- Keep profile there.

## Important constraints

- Do not break backend contract. Send only accepted fields in scan request.
- Frontend-only scan options can remain frontend state.
- Keep German copy.
- Light mode only.
- No purple gradients, no glassmorphism, no bloated cards.
- Avoid a massive fixed min-height that creates dead space.
- Do not delete required functionality.

## Verification

After changes:
1. Run `cd frontend && npm run build`.
2. If browser available, inspect at `http://127.0.0.1:5173`.
3. Confirm no default scrolling at 1280×720.
4. In final report, explicitly say what you changed to fix:
   - dead whitespace
   - cramped controls
   - disconnected scan button
   - generic form look
