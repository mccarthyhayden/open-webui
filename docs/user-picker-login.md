# User Picker Login

User Picker Login is an optional sign-in screen for small trusted or local deployments. When it is enabled, the login page lists only the accounts an administrator configured. A person chooses their name, then enters that account's password.

The feature is **disabled by default**. Existing installations keep the normal email and password form.

It does not bypass authentication. The selected account's email is submitted to the existing email and password sign-in endpoint together with the password that was typed. Password verification, sessions, and OAuth/OIDC behavior stay the same.

The login page does not receive the user database. Unauthenticated clients receive a display name, the email used to sign in, and an optional avatar URL. Roles, user ids, permissions, and other account metadata are not included. When the feature is off, or when no accounts are configured, that list is not sent and the normal login form is used.

Do not enable this on a public server if the login page should not reveal which accounts exist.

## Configure

1. Open **Admin Panel → Settings → Authentication**.
2. Turn on **User Picker Login**.
3. Add each account that should appear. Each entry needs a display name and email. An avatar URL is optional (`https://...` or a same-site path such as `/static/avatar.png`).
4. Save.

Leave the list empty to keep the normal login form even if the switch is on. People can still choose **Use email instead** when the regular login form is enabled.

The login form cannot be turned off unless someone can still sign in. That means User Picker Login is on and has at least one person, or SSO, LDAP, or trusted-header sign-in is already enabled. This avoids locking the instance with no way back in.

Environment variables set the initial values. Admin settings override them when persistent config is enabled:

- `ENABLE_USER_PICKER_LOGIN` — `False` by default
- `USER_PICKER_USERS` — JSON list, `[]` by default

```json
[
  {
    "name": "Ada",
    "email": "ada@example.com",
    "profile_image_url": ""
  },
  {
    "name": "Grace",
    "email": "grace@example.com"
  }
]
```
