# Security notice — action required

A previous version of `bot_mobile.py` contained YouTube session-cookie values directly in source code. Those values have been removed from this repaired copy.

If this repository was ever public, the owner of the affected YouTube/Google account should immediately sign out of all devices or revoke active Google sessions, change the account password, enable two-step verification, and remove the values from the public Git history. Treat exposed browser-session cookies like passwords.

This copy only reads cookies a signed-in panel user explicitly saves to their own local `user_data/<id>/yt_cookies.txt` file. Do not commit that file, `oauth_config.json`, `users.db`, or `.secret_key`.
