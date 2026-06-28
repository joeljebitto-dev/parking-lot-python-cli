from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass

from parking_lot.database import get_connection, resolve_db_path
from parking_lot.models import VehicleType


DEMO_USERS = [
    (1001, "Aarav", "Sharma", "aarav.demo@example.com", "+91-98765-43210", "active", "2026-01-15"),
    (1002, "Priya", "Nair", "priya.demo@example.com", "+91-98765-43211", "active", "2026-02-03"),
    (1003, "Rohan", "Mehta", "rohan.demo@example.com", "+91-98765-43212", "inactive", "2026-02-18"),
    (1004, "Ananya", "Rao", "ananya.demo@example.com", "+91-98765-43213", "active", "2026-03-01"),
    (1005, "Vikram", "Singh", "vikram.demo@example.com", "+91-98765-43214", "active", "2026-03-12"),
    (1006, "Neha", "Patel", "neha.demo@example.com", "+91-98765-43215", "pending", "2026-04-05"),
    (1007, "Kabir", "Khan", "kabir.demo@example.com", "+91-98765-43216", "active", "2026-04-21"),
    (1008, "Isha", "Gupta", "isha.demo@example.com", "+91-98765-43217", "inactive", "2026-05-08"),
    (1009, "Arjun", "Iyer", "arjun.demo@example.com", "+91-98765-43218", "active", "2026-05-19"),
    (1010, "Meera", "Joshi", "meera.demo@example.com", "+91-98765-43219", "pending", "2026-06-02"),
]

DEMO_USER_IDS = tuple(user[0] for user in DEMO_USERS)
DEMO_EMAILS = tuple(user[3] for user in DEMO_USERS)
DEMO_PLATES = tuple(f"DEMO-{plate_number:03d}" for plate_number in range(1, 31))

DEMO_SPACE_TARGETS = [
    ("small", VehicleType.BIKE, 2),
    ("small", VehicleType.CAR_MINI, 2),
    ("small", VehicleType.CAR_SUV, 1),
    ("mixed", VehicleType.BIKE, 2),
    ("mixed", VehicleType.CAR_MINI, 3),
    ("mixed", VehicleType.CAR_SUV, 2),
    ("mixed", VehicleType.TRUCK_MINI, 2),
    ("mixed", VehicleType.TRUCK_LARGE, 1),
    ("truck_friendly", VehicleType.CAR_MINI, 1),
    ("truck_friendly", VehicleType.CAR_SUV, 1),
    ("truck_friendly", VehicleType.TRUCK_MINI, 3),
    ("truck_friendly", VehicleType.TRUCK_LARGE, 3),
    ("very_large_complex", VehicleType.BIKE, 2),
    ("very_large_complex", VehicleType.CAR_MINI, 2),
    ("very_large_complex", VehicleType.CAR_SUV, 1),
    ("very_large_complex", VehicleType.TRUCK_MINI, 1),
    ("very_large_complex", VehicleType.TRUCK_LARGE, 1),
]


@dataclass(frozen=True)
class DemoSeedResult:
    users_seeded: int
    occupied_spaces_seeded: int


def seed_demo_data(db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)) as connection:
        clear_demo_occupancy(connection)
        reset_demo_users(connection)
        seeded_spaces = seed_demo_occupancy(connection)
        connection.commit()

    return DemoSeedResult(len(DEMO_USERS), seeded_spaces)


def clear_demo_occupancy(connection):
    user_placeholders = placeholders(DEMO_USER_IDS)
    plate_placeholders = placeholders(DEMO_PLATES)
    connection.execute(
        f"""
        UPDATE parking_spaces
        SET status = 'available',
            user_id = NULL,
            license_plate = NULL
        WHERE user_id IN ({user_placeholders})
           OR license_plate IN ({plate_placeholders})
        """,
        DEMO_USER_IDS + DEMO_PLATES,
    )


def reset_demo_users(connection):
    id_placeholders = placeholders(DEMO_USER_IDS)
    email_placeholders = placeholders(DEMO_EMAILS)
    connection.execute(
        f"""
        DELETE FROM users
        WHERE id IN ({id_placeholders}) OR email IN ({email_placeholders})
        """,
        DEMO_USER_IDS + DEMO_EMAILS,
    )
    connection.executemany(
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
        DEMO_USERS,
    )


def seed_demo_occupancy(connection):
    seeded_count = 0

    for building_name, vehicle_type, count in DEMO_SPACE_TARGETS:
        for parking_space_id in get_available_space_ids(connection, building_name, vehicle_type, count):
            user_id = DEMO_USER_IDS[seeded_count % len(DEMO_USER_IDS)]
            license_plate = DEMO_PLATES[seeded_count]
            connection.execute(
                """
                UPDATE parking_spaces
                SET status = 'occupied',
                    user_id = ?,
                    license_plate = ?
                WHERE id = ?
                """,
                (user_id, license_plate, parking_space_id),
            )
            seeded_count += 1

    return seeded_count


def get_available_space_ids(connection, building_name, vehicle_type, count):
    rows = connection.execute(
        """
        SELECT ps.id
        FROM parking_spaces ps
        JOIN parking_rows pr ON pr.id = ps.parking_row_id
        JOIN building_floors bf ON bf.id = pr.building_floor_id
        JOIN building_structures bs ON bs.id = bf.building_structure_id
        JOIN vehicle_types vt ON vt.id = ps.vehicle_type_id
        WHERE bs.name = ?
          AND vt.code = ?
          AND ps.status = 'available'
        ORDER BY bf.floor_number, pr.row_number, ps.spot_number
        LIMIT ?
        """,
        (building_name, vehicle_type.name, count),
    ).fetchall()

    if len(rows) < count:
        raise ValueError(
            f"Not enough available {vehicle_type.name} spaces in {building_name} "
            f"to seed demo data."
        )

    return [row["id"] for row in rows]


def placeholders(values):
    return ", ".join("?" for _ in values)
