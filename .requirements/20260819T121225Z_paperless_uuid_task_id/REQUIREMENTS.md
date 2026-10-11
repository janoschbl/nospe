# Requirements

## As Is

`upload_document` parses a Paperless upload task identifier and forcibly converts it to an integer. Paperless-ngx upload tasks are UUIDs, so a successful upload is reported as failed with `Paperless lieferte eine ungültige Upload-Task-ID.` The scan PDF remains local.

## To Be

Nospe preserves and returns a non-empty Paperless task ID as a string, including UUIDs returned either directly or in a `task` response object. The UI contract accepts that string and continues to show the successful upload.

## Requirements

1. Accept non-empty Paperless task-ID strings without numeric coercion.
2. Keep object and direct-string response support, while rejecting missing or malformed identifiers clearly.
3. Keep the backend and TypeScript scan-response contracts aligned.

## Acceptance Criteria

1. A representative UUID response completes the upload path and is returned unchanged.
2. Direct and object-wrapped task-ID responses both work; empty, non-string, or otherwise unexpected values produce a useful error.
3. The frontend build and backend tests pass with `paperless_document_id` typed as a string.

## Testing Plan

Add mocked upload tests for direct and object-wrapped UUIDs plus invalid values. Run the focused Paperless tests, all backend tests, and the frontend production build.

## Implementation Plan

1. Add failing UUID-focused tests that define the response contract; run the focused test file.
2. Change the Paperless client to normalize valid IDs to strings; update the Pydantic and TypeScript contracts; re-run focused tests.
3. Run the full backend suite and frontend production build.
