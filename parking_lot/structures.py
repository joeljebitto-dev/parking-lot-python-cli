from collections import Counter
from copy import deepcopy

from parking_lot.models import VehicleType


def build_parking_building_structure(vehicle_types, spaces_per_row=10, rows_per_floor=10):
    structure = []
    spaces_per_floor = spaces_per_row * rows_per_floor

    for floor_start in range(0, len(vehicle_types), spaces_per_floor):
        floor_vehicle_types = vehicle_types[floor_start : floor_start + spaces_per_floor]
        floor = []

        for row_start in range(0, len(floor_vehicle_types), spaces_per_row):
            floor.append(floor_vehicle_types[row_start : row_start + spaces_per_row])

        structure.append(floor)

    return structure


SMALL_PARKING_BUILDING = [
    [
        [VehicleType.BIKE, VehicleType.BIKE, VehicleType.CAR_MINI],
        [VehicleType.CAR_MINI, VehicleType.CAR_SUV],
    ],
]

MIXED_PARKING_BUILDING = [
    [
        [VehicleType.BIKE, VehicleType.BIKE, VehicleType.CAR_MINI],
        [VehicleType.CAR_MINI, VehicleType.CAR_SUV, VehicleType.CAR_SUV],
    ],
    [
        [VehicleType.TRUCK_MINI, VehicleType.CAR_MINI],
        [VehicleType.TRUCK_LARGE, VehicleType.TRUCK_MINI],
    ],
]

TRUCK_FRIENDLY_PARKING_BUILDING = [
    [
        [VehicleType.TRUCK_MINI, VehicleType.TRUCK_MINI],
        [VehicleType.TRUCK_LARGE, VehicleType.TRUCK_LARGE],
    ],
    [
        [VehicleType.CAR_SUV, VehicleType.TRUCK_MINI],
        [VehicleType.TRUCK_LARGE, VehicleType.CAR_MINI],
    ],
]

VERY_LARGE_COMPLEX_PARKING_BUILDING = build_parking_building_structure(
    [VehicleType.BIKE] * 100
    + [VehicleType.CAR_MINI] * 100
    + [VehicleType.CAR_SUV] * 50
    + [VehicleType.TRUCK_MINI] * 30
    + [VehicleType.TRUCK_LARGE] * 15
)

PARKING_BUILDING_STRUCTURES = {
    "small": SMALL_PARKING_BUILDING,
    "mixed": MIXED_PARKING_BUILDING,
    "truck_friendly": TRUCK_FRIENDLY_PARKING_BUILDING,
    "very_large_complex": VERY_LARGE_COMPLEX_PARKING_BUILDING,
}


def get_structure_names():
    return list(PARKING_BUILDING_STRUCTURES.keys())


def get_parking_building_structure(name):
    if name not in PARKING_BUILDING_STRUCTURES:
        raise ValueError(f"Unknown parking building structure: {name}")

    return deepcopy(PARKING_BUILDING_STRUCTURES[name])


def count_vehicle_types(structure):
    return Counter(vehicle_type for floor in structure for row in floor for vehicle_type in row)
