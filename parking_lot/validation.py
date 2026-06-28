import re


VALID_USER_STATUSES = {"active", "inactive", "pending"}


def normalize_email(email):
    return email.strip().lower()


def normalize_status(status):
    return status.strip().lower()


def normalize_license_plate(license_plate):
    return " ".join(license_plate.strip().upper().split())


def validate_email(email):
    normalized_email = normalize_email(email)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise ValueError("Email must be a valid email address.")

    return normalized_email


def validate_phone(phone):
    normalized_phone = phone.strip()
    if not normalized_phone:
        raise ValueError("Phone cannot be blank.")

    return normalized_phone


def validate_status(status):
    normalized_status = normalize_status(status)
    if normalized_status not in VALID_USER_STATUSES:
        raise ValueError("Status must be active, inactive, or pending.")

    return normalized_status


def validate_name(value, field_name):
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} cannot be blank.")

    return normalized_value


def validate_license_plate(license_plate):
    normalized_license_plate = normalize_license_plate(license_plate)
    if not re.fullmatch(r"[A-Z0-9 -]{2,20}", normalized_license_plate):
        raise ValueError(
            "License plate must be 2-20 characters using letters, numbers, spaces, or hyphens."
        )

    return normalized_license_plate
