# Cursor Task: Restart Nospe UI with tauri-ui + shadcn/ui Starter

Workspace: `/root/nospe`

Hard model policy from user: use Claude Opus high/xhigh only. Do NOT use max. Do NOT use fast mode.

## User verdict

The current UI is rejected. User says it looks "crazy horrible" and wants a real restart using this starter:

https://github.com/agmmnn/tauri-ui

The starter is a Tauri 2 + shadcn/ui setup generator. A clone is available at `/tmp/tauri-ui-starter` for docs/reference. README says:

```bash
bunx create-tauri-ui@latest
cd my-app
bun install
bun run tauri dev
```

If `bun` is unavailable, use the best practical path:
- install/use bun if straightforward, OR
- use the tauri-ui repo/docs as reference and rebuild the existing frontend with shadcn/ui patterns/components, OR
- scaffold in a temp folder and migrate the useful frontend shell into `/root/nospe/frontend`.

Do NOT just polish the old broken CSS. Treat this as a fresh UI generation using shadcn/ui conventions.

## Reference image

The user attached an old Epson Scan 2 UI screenshot at:

`/root/.hermes/image_cache/img_bc1f8cbc9888.jpg`

Use it ONLY for functional specs, not style. The old UI is visually dated. Extract the scanner workflow from it:
- scanner selection
- scan/profile/settings
- document source
- document size
- image type: color / grayscale / black-white
- resolution DPI
- rotation
- skew correction
- add/edit pages after scan
- image format PDF
- file name
- folder/output path
- preview and scan actions

## Product specs for new UI

Build a clean shadcn-style desktop utility for Nospe:
- Tauri desktop app feel, not browser dashboard.
- Light mode, modern, premium, minimal.
- Compact one-screen workflow, but NOT cramped and NOT full of dead whitespace.
- All frequent scan controls visible without scrolling in a normal 1280x720 screenshot.
- Rare controls/settings behind a gear/settings sheet/dialog.
- Scanner/profile are secondary because rarely changed.
- Main job: scan with Epson DS-410 into local PDF and optionally Paperless.

## Required main screen

Create a balanced compact scanner surface, using shadcn-like components:
- Header: Nospe, small scanner/device selector or chip, small status badge, gear icon.
- Central document/preview area that makes it feel like a scanner app, not a form.
- Filename control.
- Output folder chooser/short path display.
- Compact color mode: S/W, Grau, Farbe.
- Rotation: 0°, 90°, 180°, 270°.
- Horizontal mirror toggle.
- Skew correction toggle.
- Paperless toggle.
- Primary Scan action and optional Preview action.
- Clear ready/scanning/done status.

Important: avoid the previous failure mode:
- do not cram all controls at the top
- do not leave half the app empty
- do not make giant generic pills
- do not make every control a huge dropdown/button
- do not make a dashboard with big cards

## Settings sheet/dialog

Move rare settings here:
- Scanner selector if not in header
- Profile selector
- Resolution
- Source/document feeder
- Document size
- File format
- Paperless URL/token/test/save
- Backend/status/about

## Backend/API contract

Keep existing FastAPI backend contract unchanged:
- Frontend scan request may only send fields currently accepted by backend: scanner_id, profile_id, title, push_to_paperless.
- New options can live in frontend state until backend supports them.
- Keep existing mock fallback if backend offline.
- Keep settings save/test behavior working.

## Implementation preference

Use shadcn/ui primitives/styles/components where practical:
- Button
- Input
- Badge
- Card only if needed (avoid nested card hell)
- Sheet/Dialog for settings
- Switch
- ToggleGroup / Tabs only if appropriate (no top Scan/Einstellungen tabs)
- Select only for rare settings, not all main controls

If installing official shadcn components is feasible, do it. If not, create local shadcn-style components with Tailwind/class-variance-like patterns. But the output must look like a proper shadcn desktop app, not custom slapped CSS.

## Files likely touched

- `frontend/package.json`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/components/*`
- `frontend/src/types.ts`
- config files if needed for shadcn/tailwind

Do not modify backend unless absolutely required.

## Verification

After implementation:
1. `cd frontend && npm install` if dependencies changed.
2. `cd frontend && npm run build`.
3. If dev server is running at `http://127.0.0.1:5173`, inspect visually or at least ensure it serves.
4. If possible capture a screenshot or leave it ready for Hermes to capture.
5. Final report: files changed, design direction, build result, blockers.

## Quality bar

This time the result must be visually coherent:
- balanced vertical rhythm
- obvious scan workflow
- no weird dead space
- no cramped top-only form
- native-feeling desktop utility
- shadcn-clean, not Epson-old, not SaaS-dashboard
