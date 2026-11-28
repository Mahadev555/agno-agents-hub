"""One-time, environment-driven bootstrap for the administrator account."""

import os

from pydantic import EmailStr, TypeAdapter, ValidationError

from services.auth_service import AuthService


def main() -> None:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    display_name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Administrator").strip()
    if not email or not password:
        raise SystemExit(
            "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD before running."
        )

    try:
        email = str(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError as exc:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL must be a valid email address.") from exc

    user = AuthService.bootstrap_admin(email, password, display_name)
    print(f"Administrator account ready: {user['email']} (user_id={user['user_id']})")
    print("Remove BOOTSTRAP_ADMIN_PASSWORD from the environment after bootstrap.")


if __name__ == "__main__":
    main()
