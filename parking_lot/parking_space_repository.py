from contextlib import closing

from parking_lot.database import DEFAULT_DB_PATH, get_connection, resolve_db_path
from parking_lot.models import ParkingSpace, Vehicle, VehicleType
from parking_lot.validation import validate_license_plate


PARKING_SPACE_FIELDNAMES = [
    "building_name",
    "space_id",
    "floor",
    "row",
    "spot",
    "vehicle_type",
    "status",
    "user_id",
    "license_plate",
]
DEFAULT_PARKING_SPACES_DB_PATH = DEFAULT_DB_PATH

PARKING_SPACE_SELECT_COLUMNS = """
    ps.id AS parking_space_db_id,
    bs.name AS building_name,
    ps.space_id AS space_id,
    bf.floor_number AS floor,
    pr.row_number AS "row",
    ps.spot_number AS spot,
    vt.code AS vehicle_type,
    ps.status AS status,
    COALESCE(CAST(ps.user_id AS TEXT), '') AS user_id,
    COALESCE(ps.license_plate, '') AS license_plate
"""

PARKING_SPACE_FROM_SQL = """
    FROM parking_spaces ps
    JOIN parking_rows pr ON pr.id = ps.parking_row_id
    JOIN building_floors bf ON bf.id = pr.building_floor_id
    JOIN building_structures bs ON bs.id = bf.building_structure_id
    JOIN vehicle_types vt ON vt.id = ps.vehicle_type_id
"""

PARKING_SPACE_ORDER_SQL = """
    ORDER BY bs.name, bf.floor_number, pr.row_number, ps.spot_number
"""


def ensure_parking_spaces(db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)):
        pass
    return load_parking_space_rows(db_path=resolved_db_path)


def load_parking_space_rows(db_path=None, initialize=True):
    resolved_db_path = resolve_db_path(db_path)
    if not initialize and not resolved_db_path.exists():
        return []

    with closing(get_connection(resolved_db_path)) as connection:
        rows = connection.execute(
            f"""
            SELECT {PARKING_SPACE_SELECT_COLUMNS}
            {PARKING_SPACE_FROM_SQL}
            {PARKING_SPACE_ORDER_SQL}
            """
        ).fetchall()

    return [parking_space_row_to_public_record(row) for row in rows]


def load_parking_spaces(
    building_name,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    rows = load_parking_space_rows(db_path=resolved_db_path)
    spaces = []

    for row in rows:
        if row["building_name"] != building_name:
            continue

        vehicle_type = VehicleType.from_value(row["vehicle_type"])
        parked_vehicle = None
        if row["status"] == "occupied":
            parked_vehicle = row_to_vehicle(row, db_path=resolved_db_path)

        spaces.append(
            ParkingSpace(
                row["building_name"],
                row["space_id"],
                row["floor"],
                row["row"],
                row["spot"],
                vehicle_type,
                row["status"],
                parked_vehicle,
            )
        )

    return spaces


def park_vehicle(
    building_name,
    vehicle,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    vehicle.license_plate = validate_license_plate(vehicle.license_plate)

    with closing(get_connection(resolved_db_path)) as connection:
        ensure_license_plate_available(vehicle.license_plate, connection=connection)
        row = connection.execute(
            f"""
            SELECT {PARKING_SPACE_SELECT_COLUMNS}
            {PARKING_SPACE_FROM_SQL}
            WHERE bs.name = ?
              AND vt.code = ?
              AND ps.status = 'available'
            ORDER BY bf.floor_number, pr.row_number, ps.spot_number
            LIMIT 1
            """,
            (building_name, vehicle.vehicle_type.name),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            """
            UPDATE parking_spaces
            SET status = 'occupied',
                user_id = ?,
                license_plate = ?
            WHERE id = ?
            """,
            (
                vehicle.user.get_user_id() if vehicle.user is not None else None,
                vehicle.license_plate,
                row["parking_space_db_id"],
            ),
        )
        connection.commit()
        updated_row = fetch_parking_space_by_database_id(connection, row["parking_space_db_id"])

    return row_to_parking_space(parking_space_row_to_public_record(updated_row), vehicle)


def remove_vehicle_from_space(
    building_name,
    space_id,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    with closing(get_connection(resolved_db_path)) as connection:
        row = connection.execute(
            f"""
            SELECT {PARKING_SPACE_SELECT_COLUMNS}
            {PARKING_SPACE_FROM_SQL}
            WHERE bs.name = ? AND UPPER(ps.space_id) = ?
            LIMIT 1
            """,
            (building_name, space_id.upper()),
        ).fetchone()

        if row is None or row["status"] != "occupied":
            return None

        vehicle = row_to_vehicle(
            parking_space_row_to_public_record(row),
            db_path=resolved_db_path,
        )
        clear_occupancy_by_database_id(connection, row["parking_space_db_id"])
        connection.commit()
        return vehicle


def remove_vehicle_by_license_plate(
    license_plate,
    db_path=None,
):
    resolved_db_path = resolve_db_path(db_path)
    normalized_license_plate = validate_license_plate(license_plate)

    with closing(get_connection(resolved_db_path)) as connection:
        row = connection.execute(
            f"""
            SELECT {PARKING_SPACE_SELECT_COLUMNS}
            {PARKING_SPACE_FROM_SQL}
            WHERE ps.status = 'occupied' AND UPPER(ps.license_plate) = ?
            LIMIT 1
            """,
            (normalized_license_plate,),
        ).fetchone()

        if row is None:
            return None

        vehicle = row_to_vehicle(
            parking_space_row_to_public_record(row),
            db_path=resolved_db_path,
        )
        clear_occupancy_by_database_id(connection, row["parking_space_db_id"])
        connection.commit()
        return vehicle


def find_vehicle_by_license_plate(license_plate, db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    normalized_license_plate = validate_license_plate(license_plate)

    with closing(get_connection(resolved_db_path)) as connection:
        row = connection.execute(
            f"""
            SELECT {PARKING_SPACE_SELECT_COLUMNS}
            {PARKING_SPACE_FROM_SQL}
            WHERE ps.status = 'occupied' AND UPPER(ps.license_plate) = ?
            LIMIT 1
            """,
            (normalized_license_plate,),
        ).fetchone()

    return parking_space_row_to_public_record(row) if row is not None else None


def clear_user_occupancy(user_id, db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    normalized_user_id = int(user_id)

    with closing(get_connection(resolved_db_path)) as connection:
        result = connection.execute(
            """
            UPDATE parking_spaces
            SET status = 'available',
                user_id = NULL,
                license_plate = NULL
            WHERE status = 'occupied' AND user_id = ?
            """,
            (normalized_user_id,),
        )
        connection.commit()

    return result.rowcount


def clear_building_occupancy(building_name, db_path=None):
    resolved_db_path = resolve_db_path(db_path)

    with closing(get_connection(resolved_db_path)) as connection:
        result = connection.execute(
            f"""
            UPDATE parking_spaces
            SET status = 'available',
                user_id = NULL,
                license_plate = NULL
            WHERE status = 'occupied'
              AND id IN (
                  SELECT ps.id
                  {PARKING_SPACE_FROM_SQL}
                  WHERE bs.name = ?
              )
            """,
            (building_name,),
        )
        connection.commit()

    return result.rowcount


def get_building_counts(building_name, db_path=None):
    resolved_db_path = resolve_db_path(db_path)
    counts = {
        vehicle_type: {"total": 0, "occupied": 0, "available": 0}
        for vehicle_type in VehicleType
    }

    with closing(get_connection(resolved_db_path)) as connection:
        rows = connection.execute(
            f"""
            SELECT vt.code AS vehicle_type, ps.status AS status, COUNT(*) AS count
            {PARKING_SPACE_FROM_SQL}
            WHERE bs.name = ?
            GROUP BY vt.code, ps.status
            """,
            (building_name,),
        ).fetchall()

    for row in rows:
        vehicle_type = VehicleType.from_value(row["vehicle_type"])
        vehicle_type_counts = counts[vehicle_type]
        vehicle_type_counts["total"] += row["count"]

        if row["status"] == "occupied":
            vehicle_type_counts["occupied"] += row["count"]
        else:
            vehicle_type_counts["available"] += row["count"]

    return counts


def ensure_license_plate_available(license_plate, rows=None, db_path=None, connection=None):
    if rows is not None:
        for row in rows:
            if row["status"] == "occupied" and row["license_plate"].upper() == license_plate:
                raise ValueError("License plate is already parked.")
        return

    owns_connection = connection is None
    active_connection = connection or get_connection(resolve_db_path(db_path))
    try:
        row = active_connection.execute(
            """
            SELECT 1
            FROM parking_spaces
            WHERE status = 'occupied' AND UPPER(license_plate) = ?
            LIMIT 1
            """,
            (license_plate,),
        ).fetchone()
    finally:
        if owns_connection:
            active_connection.close()

    if row is not None:
        raise ValueError("License plate is already parked.")


def row_to_vehicle(row, db_path=None):
    user = None
    if row["user_id"]:
        from parking_lot.user_repository import find_user_by_id

        resolved_db_path = resolve_db_path(db_path)
        user = find_user_by_id(row["user_id"], db_path=resolved_db_path)

    return Vehicle(row["vehicle_type"], user, row["license_plate"])


def row_to_parking_space(row, vehicle=None):
    return ParkingSpace(
        row["building_name"],
        row["space_id"],
        row["floor"],
        row["row"],
        row["spot"],
        row["vehicle_type"],
        row["status"],
        vehicle,
    )


def parking_space_row_to_public_record(row):
    return {fieldname: row[fieldname] for fieldname in PARKING_SPACE_FIELDNAMES}


def fetch_parking_space_by_database_id(connection, parking_space_db_id):
    return connection.execute(
        f"""
        SELECT {PARKING_SPACE_SELECT_COLUMNS}
        {PARKING_SPACE_FROM_SQL}
        WHERE ps.id = ?
        LIMIT 1
        """,
        (parking_space_db_id,),
    ).fetchone()


def clear_occupancy_by_database_id(connection, parking_space_db_id):
    connection.execute(
        """
        UPDATE parking_spaces
        SET status = 'available',
            user_id = NULL,
            license_plate = NULL
        WHERE id = ?
        """,
        (parking_space_db_id,),
    )
