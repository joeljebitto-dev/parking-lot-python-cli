import tempfile
import unittest
from pathlib import Path

from parking_lot.building import ParkingBuilding
from parking_lot.demo_seed import DEMO_PLATES, DEMO_USER_IDS, seed_demo_data
from parking_lot.models import Vehicle, VehicleType
from parking_lot.parking_space_repository import (
    ensure_parking_spaces,
    find_vehicle_by_license_plate,
    load_parking_space_rows,
)
from parking_lot.structures import get_parking_building_structure
from parking_lot.user_repository import (
    create_user,
    delete_user,
    find_user_by_id,
    load_users,
    update_user,
)


class UserRepositoryTests(unittest.TestCase):
    def test_create_update_delete_user_from_temp_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            ensure_parking_spaces(db_path=db_path)

            user = create_user(
                "Test",
                "User",
                "test.user@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )
            updated_user = update_user(
                user.get_user_id(),
                email="updated.user@example.com",
                status="inactive",
                db_path=db_path,
            )
            deleted_user = delete_user(
                user.get_user_id(),
                db_path=db_path,
            )

            users = load_users(db_path=db_path)

        self.assertEqual(1, user.get_user_id())
        self.assertEqual("updated.user@example.com", updated_user.get_email())
        self.assertEqual("inactive", updated_user.get_status())
        self.assertEqual("Test User", deleted_user.get_full_name())
        self.assertEqual([], users)

    def test_duplicate_email_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            create_user(
                "First",
                "User",
                "duplicate@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )

            with self.assertRaises(ValueError):
                create_user(
                    "Second",
                    "User",
                    "DUPLICATE@example.com",
                    "+91-90000-00001",
                    db_path=db_path,
                )


class DemoSeedTests(unittest.TestCase):
    def test_seed_demo_data_creates_users_and_occupied_spaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            result = seed_demo_data(db_path=db_path)
            users = load_users(db_path=db_path)
            rows = load_parking_space_rows(db_path=db_path)
            occupied_rows = [row for row in rows if row["status"] == "occupied"]

        self.assertEqual(10, result.users_seeded)
        self.assertEqual(30, result.occupied_spaces_seeded)
        self.assertEqual(set(DEMO_USER_IDS), {user.get_user_id() for user in users})
        self.assertEqual(30, len(occupied_rows))
        self.assertEqual(set(DEMO_PLATES), {row["license_plate"] for row in occupied_rows})

    def test_seed_demo_data_is_idempotent_and_resets_demo_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            seed_demo_data(db_path=db_path)
            update_user(1001, first_name="Changed", db_path=db_path)

            result = seed_demo_data(db_path=db_path)
            users = load_users(db_path=db_path)
            rows = load_parking_space_rows(db_path=db_path)
            occupied_rows = [row for row in rows if row["status"] == "occupied"]
            reset_user = find_user_by_id(1001, db_path=db_path)

        self.assertEqual(10, len(users))
        self.assertEqual(30, result.occupied_spaces_seeded)
        self.assertEqual(30, len(occupied_rows))
        self.assertEqual("Aarav", reset_user.get_first_name())
        self.assertEqual(set(DEMO_PLATES), {row["license_plate"] for row in occupied_rows})

    def test_demo_plates_are_findable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            seed_demo_data(db_path=db_path)
            found_rows = [
                find_vehicle_by_license_plate(license_plate, db_path=db_path)
                for license_plate in DEMO_PLATES
            ]

        self.assertTrue(all(row is not None for row in found_rows))
        self.assertEqual(set(DEMO_PLATES), {row["license_plate"] for row in found_rows})

    def test_seed_demo_data_preserves_non_demo_users_and_vehicles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            user = create_user(
                "Local",
                "Driver",
                "local.driver@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )
            building = ParkingBuilding("very_large_complex", db_path=db_path)
            building.park_vehicle(Vehicle(VehicleType.BIKE, user, "LOCAL-001"))

            seed_demo_data(db_path=db_path)
            users = load_users(db_path=db_path)
            rows = load_parking_space_rows(db_path=db_path)
            local_vehicle = find_vehicle_by_license_plate("LOCAL-001", db_path=db_path)

        self.assertIsNotNone(local_vehicle)
        self.assertEqual(str(user.get_user_id()), local_vehicle["user_id"])
        self.assertIn(user.get_user_id(), {existing_user.get_user_id() for existing_user in users})
        self.assertEqual(
            30,
            len([row for row in rows if row["license_plate"] in DEMO_PLATES]),
        )


class ParkingBuildingTests(unittest.TestCase):
    def test_parking_spaces_db_generation_for_all_structures(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            rows = ensure_parking_spaces(db_path=db_path)

        self.assertEqual(318, len(rows))
        self.assertEqual(
            {"small", "mixed", "truck_friendly", "very_large_complex"},
            {row["building_name"] for row in rows},
        )

    def test_very_large_complex_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            ensure_parking_spaces(db_path=db_path)
            building = ParkingBuilding(
                "very_large_complex",
                db_path=db_path,
            )
            counts = building.get_space_counts()

        self.assertEqual(100, counts[VehicleType.BIKE]["total"])
        self.assertEqual(100, counts[VehicleType.CAR_MINI]["total"])
        self.assertEqual(50, counts[VehicleType.CAR_SUV]["total"])
        self.assertEqual(30, counts[VehicleType.TRUCK_MINI]["total"])
        self.assertEqual(15, counts[VehicleType.TRUCK_LARGE]["total"])

    def test_park_persists_and_remove_clears_db_occupancy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            ensure_parking_spaces(db_path=db_path)
            user = create_user(
                "Test",
                "User",
                "test.user@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )
            building = ParkingBuilding(
                "mixed",
                db_path=db_path,
            )

            space = building.park_vehicle(Vehicle(VehicleType.BIKE, user, "KA01AB1234"))
            reloaded_building = ParkingBuilding(
                "mixed",
                db_path=db_path,
            )
            reloaded_space = reloaded_building.find_space_by_id(space.space_id)
            removed_vehicle = reloaded_building.remove_vehicle_from_space(space.space_id)
            rows = load_parking_space_rows(db_path=db_path)
            cleared_row = next(
                row
                for row in rows
                if row["building_name"] == "mixed" and row["space_id"] == space.space_id
            )

        self.assertEqual("F1-R1-S1", space.space_id)
        self.assertFalse(reloaded_space.is_available())
        self.assertEqual("KA01AB1234", reloaded_space.parked_vehicle.license_plate)
        self.assertEqual("KA01AB1234", removed_vehicle.license_plate)
        self.assertEqual("available", cleared_row["status"])
        self.assertEqual("", cleared_row["user_id"])
        self.assertEqual("", cleared_row["license_plate"])

    def test_duplicate_occupied_license_plate_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            ensure_parking_spaces(db_path=db_path)
            user = create_user(
                "Test",
                "User",
                "test.user@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )
            building = ParkingBuilding(
                "mixed",
                db_path=db_path,
            )
            building.park_vehicle(Vehicle(VehicleType.BIKE, user, "KA01AB1234"))

            with self.assertRaises(ValueError):
                building.park_vehicle(Vehicle(VehicleType.BIKE, user, "ka01ab1234"))

    def test_deleting_user_clears_their_occupied_spaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "parking_lot.db"
            ensure_parking_spaces(db_path=db_path)
            user = create_user(
                "Test",
                "User",
                "test.user@example.com",
                "+91-90000-00000",
                db_path=db_path,
            )
            building = ParkingBuilding(
                "mixed",
                db_path=db_path,
            )
            building.park_vehicle(Vehicle(VehicleType.BIKE, user, "KA01AB1234"))

            delete_user(
                user.get_user_id(),
                db_path=db_path,
            )
            reloaded_building = ParkingBuilding(
                "mixed",
                db_path=db_path,
            )

        self.assertTrue(all(space.is_available() for space in reloaded_building.iter_spaces()))

    def test_unknown_structure_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_parking_building_structure("missing")


if __name__ == "__main__":
    unittest.main()
