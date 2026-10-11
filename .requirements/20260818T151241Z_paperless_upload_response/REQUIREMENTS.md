# Requirements

## As Is

`upload_document` assumes Paperless returns a JSON object and calls `.get("task")`. The configured Paperless instance returns a JSON string task identifier, causing `'str' object has no attribute 'get'` after the local scan succeeds.

## To Be

Paperless upload accepts both documented/object responses and string task identifiers, and reports malformed unexpected responses clearly without losing the local scan.

## Requirements

1. Parse a string response as the Paperless task identifier.
2. Retain object response support for `task` and validate unexpected payloads.

## Acceptance Criteria

1. A JSON string task ID returns an integer ID without an exception.
2. A JSON object containing `task` returns that task ID.
3. An invalid response raises a useful upload error.

## Testing Plan

Add focused mocked `httpx.post` tests for string, object, and malformed responses; run full backend tests and package smoke test.

## Implementation Plan

1. Add failing response-shape tests.
2. Normalize the parsed Paperless response safely.
3. Run tests, rebuild sidecar/app, and verify upload behavior through the running backend.
