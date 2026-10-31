# Feature notes

- Authentication: signup, login, logout, password change, account deletion.
- Passwords: PBKDF2-HMAC-SHA256 with per-password salt.
- Sessions: signed, HttpOnly cookie; local-only default binding.
- Data: SQLite with each item associated with its owner account.
- Workspace modules: dashboard, tasks, reminders, calendar events, study subjects, transactions, notes, search/filter, JSON export.
- Voice: browser speech recognition and speech synthesis where supported.
- Assistant: free local command helpers for task/reminder lookup and study/expense summaries. This is not a general LLM and does not require an API key.

## Limitations to know

- This is a local-first personal app, not a production-hardened public service.
- Browser voice recognition support varies and may use a browser/cloud speech service.
- The notification button requests permission but does not implement reliable scheduled push notifications while the app is closed.
- Calendar currently lists saved events and reminders; it is not a full month-grid calendar.
- Notes are text notes; arbitrary document uploads are not implemented in this version.
- Forgot-password email recovery and external AI are not included.
