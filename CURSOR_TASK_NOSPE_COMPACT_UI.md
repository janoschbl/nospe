# Cursor Task: Nospe Ultra-Compact One-Screen UI Revision

Workspace: `/root/nospe`

Use Claude Opus high/xhigh only, not max, not fast. Follow installed Impeccable skill/design discipline, but keep the work practical and concise.

## User feedback to implement

The latest light UI is too tall and scroll-heavy. Redesign it again to be **much more compact**.

User wants:
- Everything important reachable on **one screen without scrolling** in the default scanner window.
- Very slim, minimal, light-mode utility UI.
- No large sections, no big buttons/dropdowns everywhere.
- Remove the top `Scannen / Einstellungen` tabs.
- Default screen is just scanning.
- Settings should be behind a small gear/settings icon in a corner.
- Scanner and profile are rarely changed, so keep them tiny/secondary; profile should move into settings if possible.
- Scanner can be a small compact selector/chip because normally it does not change.
- Keep only important scan controls visible.
- Remove all unimportant/verbose UI.

## Important visible controls on the main screen

Fit these without scrolling:
- Output folder / folder select
- File name
- Rotate
- Black/white mode (`Schwarzweiß`), plus maybe compact color mode options if space permits
- Scanner select, but small/subtle
- Horizontal mirror (`Horizontal spiegeln`)
- Scan action
- Paperless toggle only if compact; otherwise move detailed Paperless settings to gear/settings

Profile should not be prominent; move to settings or a very small secondary control.

## Design constraints

- Light mode only.
- Modern but not flashy.
- Compact density is more important than spacious cards.
- Target a portrait utility window around 420–500px wide and 560–680px tall.
- Avoid scrolling in default viewport.
- Use small rows, chips, segmented buttons, icon buttons, compact form controls.
- One clear primary scan button, but not oversized. The scan button can sit at bottom and be sticky inside the app shell.
- Minimize copy. German labels only.
- Keep online/mock status small.
- Use hairline separators, not giant nested cards.
- No generic SaaS purple gradients.

## Suggested structure

Header row:
- Small brand: Nospe
- Tiny scanner chip/select and online dot
- Gear icon button for settings

Main compact form:
- Dateiname input
- Zielordner row with compact path + small folder button
- Mode row: Schwarzweiß / Grau / Farbe as compact segmented control
- Rotate row: 0 / 90 / 180 / 270 compact segmented control
- Toggle row: Horizontal spiegeln, Schräglage korrigieren maybe
- Optional compact Paperless toggle

Footer/action row:
- Small preview button if it fits
- Primary `Scannen` button
- Tiny status/progress text

Settings view/panel (via gear):
- Profile select
- Scanner select if not already enough in header
- Resolution, source, page size, file format
- Paperless URL/token/settings if currently present
- Keep existing settings behavior working

## Implementation scope

Modify frontend only:
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/components/ScanPanel.tsx`
- `frontend/src/components/SettingsPanel.tsx`
- `frontend/src/types.ts` if needed

Keep backend/API behavior working. If backend does not accept rotate/mirror/etc., keep values in frontend state only and send only accepted fields.

## Verification

After implementing:
1. `cd frontend && npm run build`
2. Run/verify app at `http://127.0.0.1:5173` if possible.
3. Confirm in final report that default UI fits one screen without scrolling at 1280x720 browser screenshot.
4. Report files changed, build result, and any blockers.
