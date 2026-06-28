from parking_lot.models import Vehicle
from parking_lot.parking_space_repository import (
    DEFAULT_PARKING_SPACES_DB_PATH,
    clear_building_occupancy,
    get_building_counts,
    load_parking_spaces,
    park_vehicle,
    remove_vehicle_from_space,
)
from parking_lot.structures import get_structure_names


class ParkingBuilding:
    def __init__(
        self,
        building_name,
        db_path=DEFAULT_PARKING_SPACES_DB_PATH,
    ):
        if building_name not in get_structure_names():
            raise ValueError(f"Unknown parking building structure: {building_name}")

        self.building_name = building_name
        self.db_path = db_path
        self.parking_spaces = []
        self.reload()

    def reload(self):
        self.parking_spaces = load_parking_spaces(
            self.building_name,
            db_path=self.db_path,
        )
        return self.parking_spaces

    def get_parking_spaces(self):
        return self.parking_spaces

    def get_space(self, floor_index, row_index, space_index):
        expected_floor = floor_index + 1
        expected_row = row_index + 1
        expected_spot = space_index + 1

        for space in self.iter_spaces():
            if (
                space.floor == expected_floor
                and space.row == expected_row
                and space.spot == expected_spot
            ):
                return space

        return None

    def iter_spaces(self):
        yield from self.parking_spaces

    def find_space_by_id(self, space_id):
        normalized_space_id = space_id.strip().upper()

        for space in self.iter_spaces():
            if space.space_id.upper() == normalized_space_id:
                return space

        return None

    def find_available_space(self, vehicle: Vehicle):
        for space in self.iter_spaces():
            if space.can_park(vehicle):
                return space

        return None

    def park_vehicle(self, vehicle: Vehicle):
        space = park_vehicle(
            self.building_name,
            vehicle,
            db_path=self.db_path,
        )
        self.reload()
        return space

    def remove_vehicle_from_space(self, space_id):
        vehicle = remove_vehicle_from_space(
            self.building_name,
            space_id,
            db_path=self.db_path,
        )
        self.reload()
        return vehicle

    def clear_occupancy(self):
        cleared_count = clear_building_occupancy(
            self.building_name,
            db_path=self.db_path,
        )
        self.reload()
        return cleared_count

    def get_space_counts(self):
        return get_building_counts(
            self.building_name,
            db_path=self.db_path,
        )
