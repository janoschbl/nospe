---
target: "Whole app UI: App shell, scan panel, and settings sheet"
total_score: 22
p0_count: 0
p1_count: 2
timestamp: 2026-06-02T17-18-31Z
slug: frontend-src-app-tsx
---
#### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Scan progress and success are visible, but backend/Paperless readiness and recovery are too subtle. |
| 2 | Match System / Real World | 3 | German scan language is mostly natural, but "Paperless", "Entzerren", and the unavailable preview need more context. |
| 3 | User Control and Freedom | 2 | Users can change settings and close the sheet, but cannot cancel an active scan or recover from the preview stub. |
| 4 | Consistency and Standards | 3 | Component vocabulary is consistent, though the scanner pill and settings icon duplicate the same destination. |
| 5 | Error Prevention | 2 | Paperless can stay enabled without visible readiness, and settings inputs have little validation guidance. |
| 6 | Recognition Rather Than Recall | 3 | Main controls are labeled and visible, but trust-critical details live in the hidden sheet/log. |
| 7 | Flexibility and Efficiency | 1 | No visible keyboard shortcuts, recent destinations, quick profiles, or batch-oriented accelerators. |
| 8 | Aesthetic and Minimalist Design | 2 | Clean foundation, but the desktop layout stretches into empty horizontal space and feels generic. |
| 9 | Error Recovery | 2 | Error messages can surface, but they do not tell users exactly what to fix next. |
| 10 | Help and Documentation | 1 | No contextual help for Paperless, folder behavior, preview availability, or scanner recovery. |
| **Total** | | **22/40** | **Acceptable, significant improvements needed before users fully trust it** |

#### Anti-Patterns Verdict

**LLM assessment**: This does not scream "AI landing page", which is good for a product UI, but it does read like an unclaimed shadcn utility. The layout has the common AI-tool smell of a tidy neutral shell, icon badge, large status card, segmented controls, three equal toggles, and a big primary button with very little product-specific opinion. The bigger issue is not decoration. It is that trust evidence, scanner health, Paperless readiness, and log detail are split between a tiny header pill, a hidden settings sheet, and transient status copy.

**Deterministic scan**: The bundled detector was attempted with `node C:\Users\block\.agents\skills\impeccable\scripts\detect.mjs --json frontend/src`, but this skill installation returned `Error: bundled detector not found.` No deterministic findings were available.

**Visual overlays**: No reliable user-visible overlay is available because the detector entrypoint was missing, so no detector script could be injected. Browser fallback evidence came from accessibility snapshots, screenshots, settings sheet inspection, backend API confirmation, and a scan-flow interaction.

#### Overall Impression

Nospe has a solid base for a compact scanner tool: labeled controls, a visible scan status region, good default grouping, and a main action that is easy to find. The single biggest opportunity is to make trust visible without forcing the user into settings. A home/office user should know at a glance: scanner ready, destination set, Paperless ready or off, next scan will save here, last scan succeeded here.

#### What's Working

- The scan status card is the right anchor. During a scan it changes text, disables controls, shows progress, and returns with a saved path.
- The primary workflow is mostly direct. Filename, destination, mode, rotation, options, preview, and scan are all in one place.
- The settings sheet uses familiar product patterns: sections, selects, input labels, footer actions, and an activity log.

#### Priority Issues

- **[P1] What**: Trust-critical readiness is hidden or too subtle.
  **Why it matters**: The user selected trust and clarity as the critique priority. Right now the header has a small scanner pill, the main card says "Bereit zum Scannen", and Paperless state lives mostly in settings/logs. A user can start a scan without knowing whether Paperless is configured, whether upload is expected to work, or where the scan will go in full.
  **Fix**: Add a compact readiness strip under the hero or above the action bar: scanner, save folder, Paperless state. Use plain states like "Scanner verbunden", "Speichert nach Documents\Scans", "Paperless bereit" or "Paperless nicht eingerichtet".
  **Suggested command**: `/impeccable clarify`

- **[P1] What**: The main desktop layout stretches instead of feeling like a compact utility.
  **Why it matters**: In the browser at 1024px, controls run across a wide blank surface and the app feels less intentional than the compact portrait Tauri goal. For a small Windows scanner utility, excess width weakens hierarchy and makes controls harder to scan.
  **Fix**: Constrain the main workflow to a deliberate max width, then use the remaining surface only if it carries useful trust context such as a recent scans rail or persistent activity. In the Tauri window, tune for the actual target dimensions instead of a web page canvas.
  **Suggested command**: `/impeccable layout`

- **[P2] What**: "Vorschau" is an enabled-looking secondary action that only says it is unavailable.
  **Why it matters**: Preview sounds like a real scanner function. A home/office user will click it to reduce risk before scanning, then lose confidence when it behaves like a stub.
  **Fix**: Either hide it until implemented, label it "Vorschau bald verfügbar", or convert it into a useful low-risk action such as "Testscan" if the backend supports it.
  **Suggested command**: `/impeccable harden`

- **[P2] What**: Paperless upload is treated as a simple toggle, not a readiness-dependent workflow.
  **Why it matters**: Upload failure is a high-trust moment. The user needs to know before scanning whether a token and URL are configured and after scanning whether upload succeeded independently from PDF saving.
  **Fix**: Split local save success from upload success in the hero. Disable or warn on the Paperless toggle when connection is untested or not configured. Link directly to the Paperless settings section when attention is needed.
  **Suggested command**: `/impeccable harden`

- **[P2] What**: The app has little product identity beyond default neutral shadcn.
  **Why it matters**: Product UI can be familiar, but this currently feels generic. A scanner tool benefits from a subtle identity tied to paper, clarity, and reliable machinery.
  **Fix**: Introduce a restrained color strategy with tinted neutrals and one scan-state accent, plus a more specific document/status treatment. Avoid decorative branding. Make the states feel owned.
  **Suggested command**: `/impeccable colorize`

#### Cognitive Load

Moderate cognitive load: 3 checklist failures.

- **Visual hierarchy**: The primary button is clear, but scanner state, destination, Paperless state, and last result compete across separate areas.
- **Progressive disclosure**: Settings are disclosed in a sheet, which is good, but the main screen hides too much readiness context.
- **One thing at a time**: The main surface asks the user to consider filename, destination, mode, rotation, three toggles, preview, and scan at once. This is manageable, but not yet sequenced around the trust question: "Can I scan safely now?"

Decision points mostly stay within 4 options: mode has 3, rotation has 4, options has 3. The settings sheet is denser, but acceptable for less frequent changes.

#### Emotional Journey

The current journey starts calm, but not fully reassuring. The peak moment, pressing "Scannen", works: progress is immediate and the final state shows "Letzter Scan gespeichert" with a path. The end state is underpowered because it truncates the path and does not separately confirm Paperless upload. The emotional valley is before scanning: the user has to infer from a small pill and a hidden log whether the scanner and upload path are genuinely ready.

#### Persona Red Flags

**Jordan (First-Timer)**: Jordan sees labeled controls, which helps, but does not get a plain explanation of Paperless, what "Entzerren" does, or why preview is present if it is not available. If scanner detection fails, "Kein Scanner" plus disabled scan actions lacks a direct explanation on the main surface.

**Sam (Accessibility-Dependent User)**: Core controls are keyboard-reachable and labeled in the accessibility tree. State still leans on color and a visual document icon. The progress bar is hidden from assistive tech when idle, but there is no obvious live-region announcement for phase changes and scan completion.

**Alex (Power User)**: Alex can scan quickly once defaults are right, but there are no visible accelerators: no keyboard shortcut for scan, no quick profile control on the main screen, no recent destinations, no batch count, and no cancel during an active scan.

#### Minor Observations

- The scanner pill and settings icon both open settings. This is defensible, but the pill should more clearly read as status first and control second.
- The activity log duplicates "Backend verbunden" entries after reloads, which makes the log feel noisier than the actual state.
- The settings sheet title "Selten geänderte Optionen" is accurate, but it weakens confidence when it contains important operational details like scanner, destination, Paperless, and log.
- The Tauri config reportedly uses a dark window theme while the web UI forces light mode. Align the chrome and app surface.
- The success color treatment is pleasant, but the full-width success card can feel oversized relative to the small amount of content it confirms.

#### Questions to Consider

- What should the user trust before they press scan: just local PDF save, or local PDF plus Paperless upload?
- Should Nospe optimize for one-click scanning, or for confidence review before every scan?
- Is "Vorschau" a committed feature for MVP, or should the current UI stop advertising it?
- What would make the app feel like a dependable scanner appliance instead of a generic settings form?
