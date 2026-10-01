"""User Picker Login helpers.

This feature is for small trusted or local deployments. It is disabled by
default. The login page may show an admin-chosen list of accounts so someone
can pick a name and type a password. It does not bypass password authentication,
and it must never expose the user database.
"""

from __future__ import annotations

from urllib.parse import urlparse

from open_webui.utils.misc import validate_email_format

USER_PICKER_MAX_USERS = 50
USER_PICKER_NAME_MAX_LENGTH = 128
USER_PICKER_EMAIL_MAX_LENGTH = 320
USER_PICKER_URL_MAX_LENGTH = 2048


def is_safe_avatar_url(url: str) -> bool:
    """Allow http(s) URLs and same-site paths. Reject scripts and traversal."""
    if not url or len(url) > USER_PICKER_URL_MAX_LENGTH or '\\' in url or '..' in url:
        return False
    if url.startswith('/') and not url.startswith('//'):
        return True
    parsed = urlparse(url)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def _clean_entry(entry) -> dict | None:
    if not isinstance(entry, dict):
        return None

    name = str(entry.get('name') or '').strip()
    email = str(entry.get('email') or '').strip().lower()
    avatar = str(entry.get('profile_image_url') or '').strip()

    if not name or len(name) > USER_PICKER_NAME_MAX_LENGTH:
        return None
    if not email or len(email) > USER_PICKER_EMAIL_MAX_LENGTH or not validate_email_format(email):
        return None
    if avatar and not is_safe_avatar_url(avatar):
        avatar = ''

    # Only the fields the login page needs. Roles, ids, and other metadata stay out.
    return {
        'name': name,
        'email': email,
        'profile_image_url': avatar,
    }


def normalize_user_picker_users(users) -> list[dict]:
    """Drop invalid or sensitive fields. Used for public config and defaults."""
    if not isinstance(users, list):
        return []

    cleaned = []
    seen = set()
    for entry in users:
        if len(cleaned) >= USER_PICKER_MAX_USERS:
            break
        item = _clean_entry(entry)
        if not item or item['email'] in seen:
            continue
        seen.add(item['email'])
        cleaned.append(item)
    return cleaned


def public_user_picker(enabled, users) -> dict:
    """Payload for the unauthenticated login page.

    When the feature is disabled, the configured list is omitted so account
    names and emails are not disclosed.
    """
    if not enabled:
        return {'enable': False, 'users': []}
    return {'enable': True, 'users': normalize_user_picker_users(users)}


def validate_user_picker_users(users) -> list[dict]:
    """Strict check for admin saves. Invalid entries are rejected, not stored."""
    if users is None:
        return []
    if not isinstance(users, list):
        raise ValueError('User picker users must be a list')
    if len(users) > USER_PICKER_MAX_USERS:
        raise ValueError(f'At most {USER_PICKER_MAX_USERS} user picker entries are allowed')

    cleaned = []
    seen = set()
    for index, entry in enumerate(users):
        if not isinstance(entry, dict):
            raise ValueError(f'User picker entry {index + 1} is invalid')

        name = str(entry.get('name') or '').strip()
        email = str(entry.get('email') or '').strip().lower()
        avatar = str(entry.get('profile_image_url') or '').strip()

        if not name:
            raise ValueError(f'User picker entry {index + 1} needs a display name')
        if len(name) > USER_PICKER_NAME_MAX_LENGTH:
            raise ValueError(f'User picker entry {index + 1} display name is too long')
        if not validate_email_format(email) or len(email) > USER_PICKER_EMAIL_MAX_LENGTH:
            raise ValueError(f'User picker entry {index + 1} has an invalid email')
        if email in seen:
            raise ValueError(f'User picker emails must be unique: {email}')
        if avatar and not is_safe_avatar_url(avatar):
            raise ValueError(f'User picker entry {index + 1} avatar must be an http(s) URL or site path')

        seen.add(email)
        cleaned.append(
            {
                'name': name,
                'email': email,
                'profile_image_url': avatar,
            }
        )
    return cleaned
