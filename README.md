# Parking Lot Problem

Interactive parking-lot manager with SQLite-backed users, building structures,
vehicle types, and parking spaces.

## Setup

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the CLI:

```bash
python3 main.py
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## CLI Flow

When the CLI starts, choose the parking building you want to operate on. Parking
actions then apply to that selected building.

Core actions:

- List, create, edit, and delete users.
- Show building structures and parking summaries.
- Park a vehicle by choosing a user, entering a license plate, and selecting a
  vehicle type. The system allocates the first compatible free space.
- Find or remove a parked vehicle by license plate.
- Remove a parked vehicle by space id.
- Clear all occupied spaces in the selected building.
- Seed resettable demo data with 10 test users and 30 occupied spaces.

Parking occupancy is persisted in `parking_lot/parking_lot.db`, so parked
vehicles remain after restarting the CLI.

## SQLite Database

The app uses Python's built-in SQLite support and creates
`parking_lot/parking_lot.db` on first use. Runtime data is stored in these
tables:

- `users`
- `vehicle_types`
- `building_structures`
- `building_floors`
- `parking_rows`
- `parking_spaces`

Normal startup creates no users or occupied spaces. Vehicle types and parking
building layouts are seeded from the predefined structures in the codebase.
`parking_spaces.status` is either `available` or `occupied`; available spaces
store `NULL` for `user_id` and `license_plate`.

Use the CLI's `Seed demo data` menu option to reset and create demo data. That
action seeds 10 test users and 30 occupied spaces across the predefined
buildings without deleting non-demo users or non-demo parked vehicles.

## Project Structure

```text
parking_lot/
  models.py                    Core dataclasses and enums
  database.py                  SQLite schema and seed data
  demo_seed.py                 Resettable demo users and occupancy
  building.py                  Selected-building parking facade
  structures.py                Predefined building layouts
  user_repository.py           User database operations
  parking_space_repository.py  Parking-space database operations
  validation.py                Input normalization and validation
  cli.py                       Rich interactive CLI
tests/
  test_parking_lot.py
```
