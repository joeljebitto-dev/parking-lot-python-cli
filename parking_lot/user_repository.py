import sqlite3
from contextlib import closing
from datetime import date

from parking_lot.database import get_connection, resolve_db_path
from parking_lot.models import User
from parking_lot.validation import (
    validate_email,
    validate_name,
    validate_phone,
    validate_status,
)


def load_users(db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, first_name, last_name, email, phone, status, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    return [row_to_user(row) for row in rows]


def create_user(
    first_name,
    last_name,
    email,
    phone,
    status="active",
    created_at=None,
    user_id=None,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    users = load_users(db_path=resolved_db_path)
    user = build_validated_user(
        user_id or get_next_user_id(db_path=resolved_db_path),
        first_name,
        last_name,
        email,
        phone,
        status,
        created_at or date.today().isoformat(),
        users,
    )

    with closing(get_connection(resolved_db_path)) as connection:
        try:
            connection.execute(
                """
                INSERT INTO users (
                    id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                user_to_record(user),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise_user_integrity_error(error)

    return user


def update_user(
    user_id,
    first_name=None,
    last_name=None,
    email=None,
    phone=None,
    status=None,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    users = load_users(db_path=resolved_db_path)
    user = find_user_by_id(user_id, users)

    if user is None:
        return None

    updated_first_name = first_name if first_name is not None else user.get_first_name()
    updated_last_name = last_name if last_name is not None else user.get_last_name()
    updated_email = email if email is not None else user.get_email()
    updated_phone = phone if phone is not None else user.get_phone()
    updated_status = status if status is not None else user.get_status()

    updated_user = build_validated_user(
        user.get_user_id(),
        updated_first_name,
        updated_last_name,
        updated_email,
        updated_phone,
        updated_status,
        user.get_created_at(),
        users,
        excluded_user_id=user.get_user_id(),
    )

    with closing(get_connection(resolved_db_path)) as connection:
        try:
            connection.execute(
                """
                UPDATE users
                SET first_name = ?,
                    last_name = ?,
                    email = ?,
                    phone = ?,
                    status = ?,
                    created_at = ?
                WHERE id = ?
                """,
                (
                    updated_user.get_first_name(),
                    updated_user.get_last_name(),
                    updated_user.get_email(),
                    updated_user.get_phone(),
                    updated_user.get_status(),
                    updated_user.get_created_at(),
                    updated_user.get_user_id(),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise_user_integrity_error(error)

    return updated_user


def delete_user(
    user_id,
    clear_parking=True,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    user = find_user_by_id(user_id, db_path=resolved_db_path)

    if user is None:
        return None

    if clear_parking:
        from parking_lot.parking_space_repository import clear_user_occupancy

        clear_user_occupancy(user.get_user_id(), db_path=resolved_db_path)

    with closing(get_connection(resolved_db_path)) as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user.get_user_id(),))
        connection.commit()

    return user


def get_next_user_id(db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)) as connection:
        row = connection.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM users").fetchone()

    return row["next_id"]


def find_user_by_id(user_id, users=None, db_path=None):
    normalized_user_id = int(user_id)

    if users is not None:
        for user in users:
            if user.get_user_id() == normalized_user_id:
                return user
        return None

    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)) as connection:
        row = connection.execute(
            """
            SELECT id, first_name, last_name, email, phone, status, created_at
            FROM users
            WHERE id = ?
            """,
            (normalized_user_id,),
        ).fetchone()

    return row_to_user(row) if row is not None else None


def build_validated_user(
    user_id,
    first_name,
    last_name,
    email,
    phone,
    status,
    created_at,
    existing_users,
    excluded_user_id=None,
):
    normalized_email = validate_email(email)
    ensure_unique_email(normalized_email, existing_users, excluded_user_id)

    return User(
        user_id,
        validate_name(first_name, "First name"),
        validate_name(last_name, "Last name"),
        normalized_email,
        validate_phone(phone),
        validate_status(status),
        created_at,
    )


def ensure_unique_email(email, users, excluded_user_id=None):
    for user in users:
        if excluded_user_id is not None and user.get_user_id() == int(excluded_user_id):
            continue
        if user.get_email().lower() == email.lower():
            raise ValueError("Email already belongs to another user.")


def user_to_record(user):
    return (
        user.get_user_id(),
        user.get_first_name(),
        user.get_last_name(),
        user.get_email(),
        user.get_phone(),
        user.get_status(),
        user.get_created_at(),
    )


def row_to_user(row):
    return User(
        row["id"],
        row["first_name"],
        row["last_name"],
        row["email"],
        row["phone"],
        row["status"],
        row["created_at"],
    )


def raise_user_integrity_error(error):
    if "users.email" in str(error).lower() or "unique constraint failed: users.email" in str(error).lower():
        raise ValueError("Email already belongs to another user.") from error
    raise error
