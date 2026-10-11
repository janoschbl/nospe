# Equalize Select Controls

## As Is
The `Zielordner` control in `ScanPanel` is a taller custom button with a leading icon block. The `Scanner` and `Dateiformat` controls are shorter select triggers without matching leading visual markers.

## To Be
The `Scanner` and `Dateiformat` controls should visually align with the `Zielordner` button height and include a leading icon/emoji-style marker before the selected value.

## Requirements
1. Match the visual height of the `Scanner` select trigger to the `Zielordner` button.
2. Match the visual height of the `Dateiformat` select trigger to the `Zielordner` button.
3. Add a leading marker before the `Scanner` selected value.
4. Add a leading marker before the `Dateiformat` selected value.
5. Preserve existing select behavior, disabled states, and menu options.

## Acceptance Criteria
1. The `Scanner` trigger uses the same base field control height as `Zielordner`.
2. The `Dateiformat` trigger uses the same base field control height as `Zielordner`.
3. The `Scanner` trigger shows a leading scanner marker before the value or placeholder.
4. The `Dateiformat` trigger shows a leading document marker before the value.
5. Selecting values, disabled rendering, and dropdown content continue to work as before.

## Testing Plan
- Run TypeScript/build validation for the frontend after the code change.
- Check lints for the edited file.
- Visually inspect the component code path to confirm the two select triggers share the same control class vocabulary as `Zielordner`.

## Implementation Plan
1. Add a small reusable leading icon wrapper for compact select triggers and test with TypeScript/build.
2. Apply the wrapper to `Scanner` and `Dateiformat` triggers while keeping the existing `SelectValue` and menu options intact, then test again.
