# Cursor Task: Nospe Modern Light Portrait UI Redesign

Workspace: `/root/nospe`

You are redesigning the existing Nospe React/Tauri MVP UI. The current backend and API already work; keep backend changes minimal unless required for UI data shape. Focus on the frontend.

## User request

The user wants the app UI redesigned from the old Epson Scan 2 style reference into a **new, modern, polished, slim portrait light-mode scanner UI**.

They explicitly requested:
- schlank im Hochformat (narrow portrait app shape, good as a desktop utility window)
- light mode
- modern, clean, polished, "geiles UI"
- inspired by the attached old Epson Scan 2 UI only in terms of functionality, not visual style
- use Impeccable skill/workflow, especially polish/critique thinking
- use Claude Opus model

## Reference image summary

Old Epson Scan 2 UI contains these core controls/functionality:
- Scanner select
- Scan settings / profile select
- Mode select
- Main/advanced settings tabs
- Document source select
- Document size select
- Image type select
- Resolution DPI select
- Rotate select
- Correct document skew select
- Add/edit pages after scanning checkbox
- Image format select (PDF)
- File name field
- Folder select
- Preview and Scan actions

Do NOT copy the old visual style. It looks dated: gray Windows form, many borders, cramped labels, default dropdowns. Preserve the useful scanning concepts and recompose them into a modern product UI.

## Impeccable docs notes

From https://impeccable.style/docs/critique:
- Use `/impeccable critique` when a page is functionally done and you want an honest design review.
- It checks Nielsen heuristics, cognitive load, personas, and AI-slop detectors.
- Watch for AI slop tells: generic gradient text, default purple palettes, nested cards, excessive borders, poor hierarchy.
- After critique, pair with `/impeccable polish` or improve the prioritized issues.

From the Designing with Impeccable summary:
- Product context matters; design serves the task.
- Pre-ship workflow should score: accessibility, performance, theming, responsive behavior, anti-patterns.
- Stress-test messy reality: German labels, long file names, offline states, error states.
- Polish microcopy, labels, empty states.

Use the project Impeccable skill installed in `.cursor/skills/impeccable/` and/or `.agents/skills/impeccable/`. If slash commands are not available in this CLI mode, still follow the Impeccable design discipline manually: critique first principles, remove AI slop, polish typography/layout/color/accessibility/responsive behavior.

## Design direction

Create a modern light-mode portrait utility app, approximately 420–520px wide as the primary layout, but still responsive on browser widths.

Suggested visual direction:
- Clean white/off-white background, soft neutral surfaces, high contrast text
- System font or Inter-like typography
- Subtle shadows and borders, not heavy nested cards
- One calm accent color (Epson-ish blue is okay, but not default SaaS purple)
- Large confident primary Scan button near the bottom/sticky action area
- Compact but readable controls
- Group settings into clear sections:
  1. Device / scanner
  2. Document settings
  3. Output
  4. Paperless
- Use modern segmented/tabs/toggles where helpful
- Make status feel premium: online badge, scan progress, last scan result
- Avoid clutter: advanced settings can be collapsed/details panel

## Required implementation scope

Modify frontend code to implement the redesigned UI:
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- components as needed under `frontend/src/components/`
- `frontend/src/types.ts` / `api.ts` only if needed

Keep existing API behavior working:
- backend online/offline detection
- scanners/profiles loading
- scan call
- paperless toggle/test/settings
- mock fallback when backend unavailable

Add UI controls for the Epson-inspired scanner options if not currently present, at least as frontend controls:
- Document source
- Document size
- Image type/color mode
- Resolution DPI
- Rotate
- Skew correction
- Add/edit pages after scanning
- Image format PDF
- File name / title
- Folder/output dir
- Preview button (can be stub UI action/log entry if backend has no preview)
- Scan button

If backend models do not support all fields, keep them in frontend state for now and only send fields the backend accepts. Do not break the backend.

## Quality bar

After implementing:
1. Run `cd frontend && npm run build`
2. If possible, run the backend and check the app in browser at `http://127.0.0.1:5173`
3. Run an Impeccable-style critique/polish pass manually or via the installed skill/CLI if possible.
4. Fix the top 3–5 issues found in your own critique.
5. Return a concise final report with:
   - files changed
   - design summary
   - build/test commands run + results
   - blockers, if any

## Constraints

- Do not make it dark mode.
- Do not use generic purple gradient SaaS styling.
- Do not overcomplicate the backend.
- Do not remove existing functionality.
- Keep it production-polished, not a quick mock.
