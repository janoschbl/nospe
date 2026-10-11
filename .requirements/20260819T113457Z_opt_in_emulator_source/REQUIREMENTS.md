# Opt-in emulator source

## As Is

The standalone emulator now starts independently on port 8766, but the backend excludes its installed virtual TWAIN source unconditionally. With no physical TWAIN driver available, Nospe therefore shows no scanner.

## To Be

Nospe lists physical Windows TWAIN sources first. When, and only when, the separately started emulator is reachable on localhost port 8766, its `Nospe Virtual Scanner` source is shown as an additional selectable source.

## Requirements

1. Detect the local emulator through a short localhost connection attempt.
2. Exclude the virtual source when the emulator is unavailable.
3. Append the virtual source after physical sources when it is available.

## Acceptance Criteria

1. A list containing only the virtual source reports zero normal scanners when the emulator is stopped.
2. The same list reports the virtual source when the emulator check succeeds.
3. A physical source precedes the virtual source, so default selection remains physical.

## Testing Plan

- Add mocked unit tests for unavailable and reachable emulator states.
- Run the TWAIN test module and smoke-test the active backend with the separate emulator running.

## Implementation Plan

1. Add failing source-list/status tests for the opt-in virtual source.
2. Implement the localhost availability check and ordered visible-source helper.
3. Run focused tests, then rebuild/restart the backend and verify scanner status.
