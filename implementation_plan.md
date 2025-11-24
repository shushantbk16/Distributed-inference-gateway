# Switch to Gemini 3 Pro Preview

## Goal
Update the application to use the `gemini-3-pro-preview` model for the Gemini provider, as requested by the user.

## Proposed Changes

### Configuration
#### [MODIFY] [src/config.py](file:///Users/shushant/Documents/P1/src/config.py)
- Update `gemini_model` default value from `gemini-1.5-flash` to `gemini-3-pro-preview`.

## Verification Plan

### Local Verification
1.  Start the application locally.
2.  Run `verify_live.py` (pointing to localhost) or a specific provider test to confirm `gemini-3-pro-preview` is accepted and working.
3.  Check logs for any API errors (e.g., 400 Bad Request if model name is invalid).

### Live Verification
- Once deployed (by user), use `verify_live.py` to verify the live endpoint.
