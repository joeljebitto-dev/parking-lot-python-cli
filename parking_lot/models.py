from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class User:
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    status: str
    created_at: str

    def __post_init__(self):
        self.user_id = int(self.user_id)

    def __str__(self):
        return (
            f"User(id={self.user_id}, name={self.get_full_name()}, "
            f"email={self.email}, phone={self.phone}, status={self.status}, "
            f"created_at={self.created_at})"
        )

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_user_id(self):
        return self.user_id

    def set_user_id(self, user_id):
        self.user_id = int(user_id)

    def get_first_name(self):
        return self.first_name

    def set_first_name(self, first_name):
        self.first_name = first_name

    def get_last_name(self):
        return self.last_name

    def set_last_name(self, last_name):
        self.last_name = last_name

    def get_email(self):
        return self.email

    def set_email(self, email):
        self.email = email

    def get_phone(self):
        return self.phone

    def set_phone(self, phone):
        self.phone = phone

    def get_status(self):
        return self.status

    def set_status(self, status):
        self.status = status

    def get_created_at(self):
        return self.created_at

    def set_created_at(self, created_at):
        self.created_at = created_at


class VehicleType(Enum):
    BIKE = 1
    CAR_MINI = 2
    CAR_SUV = 3
    TRUCK_MINI = 4
    TRUCK_LARGE = 5

    @classmethod
    def from_value(cls, value):
        if isinstance(value, VehicleType):
            return value

        normalized_value = str(value).strip().upper()
        if normalized_value in cls.__members__:
            return cls[normalized_value]

        raise ValueError(f"Unsupported vehicle type: {value}")


@dataclass
class Vehicle:
    vehicle_type: VehicleType
    user: Optional[User] = None
    license_plate: str = ""

    def __post_init__(self):
        self.vehicle_type = VehicleType.from_value(self.vehicle_type)
        self.license_plate = self.license_plate.strip().upper()


@dataclass
class ParkingSpace:
    building_name: str
    space_id: str
    floor: int
    row: int
    spot: int
    vehicle_type: VehicleType
    status: str = "available"
    parked_vehicle: Optional[Vehicle] = None

    def __post_init__(self):
        self.floor = int(self.floor)
        self.row = int(self.row)
        self.spot = int(self.spot)
        self.vehicle_type = VehicleType.from_value(self.vehicle_type)
        self.status = self.status or "available"

    def is_available(self):
        return self.status == "available" and self.parked_vehicle is None

    def can_park(self, vehicle):
        return self.is_available() and vehicle.vehicle_type == self.vehicle_type

    def park_vehicle(self, vehicle):
        if not self.can_park(vehicle):
            return False

        self.parked_vehicle = vehicle
        self.status = "occupied"
        return True

    def remove_vehicle(self):
        vehicle = self.parked_vehicle
        self.parked_vehicle = None
        self.status = "available"
        return vehicle

    def get_user_id(self):
        if self.parked_vehicle is None or self.parked_vehicle.user is None:
            return ""

        return self.parked_vehicle.user.get_user_id()

    def get_license_plate(self):
        if self.parked_vehicle is None:
            return ""

        return self.parked_vehicle.license_plate


class BikeParkingSpace(ParkingSpace):
    def __init__(self, building_name, space_id, floor, row, spot, status="available", parked_vehicle=None):
        super().__init__(
            building_name,
            space_id,
            floor,
            row,
            spot,
            VehicleType.BIKE,
            status,
            parked_vehicle,
        )


class MiniCarParkingSpace(ParkingSpace):
    def __init__(self, building_name, space_id, floor, row, spot, status="available", parked_vehicle=None):
        super().__init__(
            building_name,
            space_id,
            floor,
            row,
            spot,
            VehicleType.CAR_MINI,
            status,
            parked_vehicle,
        )


class SuvCarParkingSpace(ParkingSpace):
    def __init__(self, building_name, space_id, floor, row, spot, status="available", parked_vehicle=None):
        super().__init__(
            building_name,
            space_id,
            floor,
            row,
            spot,
            VehicleType.CAR_SUV,
            status,
            parked_vehicle,
        )


class MiniTruckParkingSpace(ParkingSpace):
    def __init__(self, building_name, space_id, floor, row, spot, status="available", parked_vehicle=None):
        super().__init__(
            building_name,
            space_id,
            floor,
            row,
            spot,
            VehicleType.TRUCK_MINI,
            status,
            parked_vehicle,
        )


class LargeTruckParkingSpace(ParkingSpace):
    def __init__(self, building_name, space_id, floor, row, spot, status="available", parked_vehicle=None):
        super().__init__(
            building_name,
            space_id,
            floor,
            row,
            spot,
            VehicleType.TRUCK_LARGE,
            status,
            parked_vehicle,
        )
