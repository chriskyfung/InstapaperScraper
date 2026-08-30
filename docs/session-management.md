# Session Management

This document explains how `instapaper-scraper` authenticates, stores and
reuses sessions, and how to troubleshoot session problems.

## Overview

The end-to-end session lifecycle:

1. **Login** (`InstapaperAuthenticator.login()`)
   - Tries to load an existing session file.
   - If that fails, performs a credential login (preflight `GET /user/login`
     for the `_xsrf` CSRF token, then `POST /user/login`).
   - On success, saves the session (see [Session file format](#session-file-format-v2)).
2. **Verification** (`_verify_session()`)
   - Probes `GET https://www.instapaper.com/data/user_session` with XHR headers.
   - A valid session returns a JSON payload containing a `user` object.
3. **Form key hand-off**
   - The `form_key` from the same payload is captured and passed to
     `InstapaperClient(form_key=...)`, so the first scraping request does not
     need an extra round-trip. If it is missing, the client falls back to
     fetching it itself (`_fetch_form_key()`).

Both `/data/*` callers (`auth.py` verification and `api.py` form-key fetch)
send identical headers (`constants.XHR_HEADERS`: `accept: application/json`,
`x-requested-with: XMLHttpRequest`). Authentication comes from the session
cookies, not from headers.

## Why `/u` verification was replaced

The original implementation verified sessions by requesting `GET /u` and
checking that the response did not contain the `login_form` marker.
Instapaper's web relaunch changed this endpoint: **it now returns 200
regardless of login state**, so the check never fired and every run silently
discarded the stored session and re-logged-in with credentials.

`/data/user_session` is used instead because it behaves differently for
authenticated vs anonymous requests:

| State | Response |
| --- | --- |
| Authenticated | `200` JSON: `{"user": {"username": ..., "form_key": ...}}` |
| Anonymous | `401 text/html` |

## Session file format (v2)

The session is stored as a JSON payload, encrypted with `Fernet`
(`.session_key` holds the key; both files have `0600` permissions):

```json
{
  "version": 2,
  "cookies": [
    {"name": "pfus", "value": "...", "domain": ".instapaper.com",
     "path": "/", "secure": false}
  ]
}
```

Design notes:

- **All cookies are persisted**, not only the `pfus`/`pfps`/`pfhs` auth
  cookies. The file is already encrypted with owner-only permissions, and
  restoring the complete cookie context (e.g. `_xsrf`) keeps the restored
  session as close as possible to the original browser context.
- The JSON payload is **immune to special characters in cookie values**.
  The legacy v1 format (`name:value:domain` per line) truncated any value
  containing `:`; v1 files are still read for backward compatibility and are
  upgraded to v2 on the next save.
- After every save, a **round-trip self-check** decrypts and re-parses the
  file and compares it with what was written. A mismatch is logged loudly at
  write time instead of surfacing later as a mysterious 401.

## Two-stage verification fallback

`_verify_session()` makes up to two attempts:

1. **Normal attempt**: a session request using the full cookie jar and
   `XHR_HEADERS`.
2. **Minimal attempt** (only if attempt 1 returns a non-OK status): retries
   with an explicit `Cookie` header containing **only** `pfus`, `pfps` and
   `pfhs`, replicating exactly this known-good browser request:

   ```sh
   curl 'https://www.instapaper.com/data/user_session' \
     -b 'pfus=...; pfps=...; pfhs=...' \
     -H 'x-requested-with: XMLHttpRequest'
   ```

   The request is sent as a bare `PreparedRequest` through the session's
   adapter so the cookie jar cannot merge any other cookies into the header.

If attempt 2 succeeds, an INFO log reports that the full jar (most likely a
stale `_xsrf`) was interfering. If both attempts fail, the stored cookie
values themselves are stale or corrupted.

Every attempt is logged at DEBUG level (`Verification attempt: ...`) with
the URL, status code, content type, the exact outgoing `Cookie` header, and
a response body snippet.

## User-Agent configuration

The default `python-requests` User-Agent can be rejected by anti-bot layers
on the `/data/*` endpoints, so the client sends a browser-like UA by default
(`InstapaperClient.DEFAULT_USER_AGENT`). It can be overridden per call with
`InstapaperClient(session, user_agent=...)` or globally with the
`INSTAPAPER_USER_AGENT` environment variable.

### Keeping the default User-Agent fresh

The default pins a specific Chrome major version, which goes stale as Chrome
ships a new major roughly every 4 weeks. Maintenance guidance:

- Check the current stable major at <https://endoflife.date/api/chrome.json>
  (the first entry's `cycle` field) and bump the version in
  `DEFAULT_USER_AGENT` when the pinned one is more than ~6 months old.
- Prefer the **current stable** version. An older (stale-but-plausible)
  version is mildly risky; a version **newer than any released stable** is a
  strong bot signal and must never be used.
- For long-lived deployments, pinning via `INSTAPAPER_USER_AGENT` lets you
  control the fingerprint independently of library upgrades.

## Troubleshooting

Use `--dump-session` to print a masked summary (first4...last4 of each
value) of the stored cookies and compare against your browser's DevTools
cookie panel:

```sh
instapaper-scraper --dump-session
```

| Log message | Meaning | Action |
| --- | --- | --- |
| `returned status 401` (both attempts) | Stored cookie values are stale, rotated or corrupted | Use `--dump-session` to compare the stored cookie values against your browser's DevTools; then delete `.instapaper_session` and `.session_key`, log in once, and the next run should reuse the fresh session |
| `no user object in /data/user_session response` | Server answered but does not consider the session logged in | Same as above; if it persists with fresh values, compare `--dump-session` output with the browser |
| `did not return JSON` | The endpoint returned HTML (its behavior changed) | Open an issue; the endpoint contract likely changed again |
| `Session verified with minimal cookie set` (INFO) | The full jar interfered (likely a stale `_xsrf`) | Harmless; report if it happens on every run |
| `Post-save self-check failed` | The file just written does not read back identically | Check disk health / file permissions; delete and re-login |

Enable DEBUG logging to see the exact request/response details of each
verification attempt.
