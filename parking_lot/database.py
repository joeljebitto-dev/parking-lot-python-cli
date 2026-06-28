from __future__ import annotations

import sqlite3
from pathlib import Path

from parking_lot.models import VehicleType
from parking_lot.structures import PARKING_BUILDING_STRUCTURES


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "parking_lot.db"


def resolve_db_path(db_path=None):
    if db_path is not None:
        return Path(db_path)

    return DEFAULT_DB_PATH


def get_connection(db_path=None):
    resolved_path = resolve_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize_database(connection)
    return connection


def initialize_database(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            phone TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'pending')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vehicle_types (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS building_structures (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS building_floors (
            id INTEGER PRIMARY KEY,
            building_structure_id INTEGER NOT NULL,
            floor_number INTEGER NOT NULL,
            UNIQUE (building_structure_id, floor_number),
            FOREIGN KEY (building_structure_id)
                REFERENCES building_structures (id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS parking_rows (
            id INTEGER PRIMARY KEY,
            building_floor_id INTEGER NOT NULL,
            row_number INTEGER NOT NULL,
            UNIQUE (building_floor_id, row_number),
            FOREIGN KEY (building_floor_id)
                REFERENCES building_floors (id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS parking_spaces (
            id INTEGER PRIMARY KEY,
            parking_row_id INTEGER NOT NULL,
            space_id TEXT NOT NULL,
            spot_number INTEGER NOT NULL,
            vehicle_type_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available', 'occupied')),
            user_id INTEGER,
            license_plate TEXT COLLATE NOCASE,
            UNIQUE (parking_row_id, spot_number),
            FOREIGN KEY (parking_row_id)
                REFERENCES parking_rows (id)
                ON DELETE CASCADE,
            FOREIGN KEY (vehicle_type_id)
                REFERENCES vehicle_types (id),
            FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE SET NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_occupied_license_plate
            ON parking_spaces (license_plate)
            WHERE status = 'occupied' AND license_plate IS NOT NULL;
        """
    )
    seed_vehicle_types(connection)
    seed_building_structures(connection)
    connection.commit()


def seed_vehicle_types(connection):
    for vehicle_type in VehicleType:
        connection.execute(
            """
            INSERT OR IGNORE INTO vehicle_types (id, code, label)
            VALUES (?, ?, ?)
            """,
            (vehicle_type.value, vehicle_type.name, format_vehicle_type_label(vehicle_type)),
        )


def seed_building_structures(connection):
    for building_name, structure in PARKING_BUILDING_STRUCTURES.items():
        building_id = get_or_create_id(
            connection,
            "building_structures",
            "name",
            building_name,
            "INSERT OR IGNORE INTO building_structures (name) VALUES (?)",
        )

        for floor_index, floor in enumerate(structure, start=1):
            floor_id = get_or_create_scoped_id(
                connection,
                "building_floors",
                "building_structure_id",
                building_id,
                "floor_number",
                floor_index,
            )

            for row_index, row in enumerate(floor, start=1):
                row_id = get_or_create_scoped_id(
                    connection,
                    "parking_rows",
                    "building_floor_id",
                    floor_id,
                    "row_number",
                    row_index,
                )

                for spot_index, vehicle_type in enumerate(row, start=1):
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO parking_spaces (
                            parking_row_id,
                            space_id,
                            spot_number,
                            vehicle_type_id,
                            status
                        )
                        VALUES (?, ?, ?, ?, 'available')
                        """,
                        (
                            row_id,
                            create_space_id(floor_index, row_index, spot_index),
                            spot_index,
                            vehicle_type.value,
                        ),
                    )


def get_or_create_id(connection, table_name, column_name, value, insert_sql):
    connection.execute(insert_sql, (value,))
    return connection.execute(
        f"SELECT id FROM {table_name} WHERE {column_name} = ?",
        (value,),
    ).fetchone()["id"]


def get_or_create_scoped_id(
    connection,
    table_name,
    scope_column_name,
    scope_value,
    value_column_name,
    value,
):
    connection.execute(
        f"""
        INSERT OR IGNORE INTO {table_name} ({scope_column_name}, {value_column_name})
        VALUES (?, ?)
        """,
        (scope_value, value),
    )
    return connection.execute(
        f"""
        SELECT id
        FROM {table_name}
        WHERE {scope_column_name} = ? AND {value_column_name} = ?
        """,
        (scope_value, value),
    ).fetchone()["id"]


def create_space_id(floor, row, spot):
    return f"F{floor}-R{row}-S{spot}"


def format_vehicle_type_label(vehicle_type):
    return vehicle_type.name.replace("_", " ").title()
