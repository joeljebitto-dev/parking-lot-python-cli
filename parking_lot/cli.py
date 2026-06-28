from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from parking_lot.building import ParkingBuilding
from parking_lot.demo_seed import seed_demo_data
from parking_lot.models import Vehicle, VehicleType
from parking_lot.parking_space_repository import (
    clear_building_occupancy,
    find_vehicle_by_license_plate,
    remove_vehicle_by_license_plate,
)
from parking_lot.structures import (
    PARKING_BUILDING_STRUCTURES,
    count_vehicle_types,
    get_structure_names,
)
from parking_lot.user_repository import (
    create_user,
    delete_user,
    find_user_by_id,
    load_users,
    update_user,
)
from parking_lot.validation import (
    VALID_USER_STATUSES,
    validate_license_plate,
)


VEHICLE_TYPE_LABELS = {
    VehicleType.BIKE: "Bike",
    VehicleType.CAR_MINI: "Mini Car",
    VehicleType.CAR_SUV: "SUV Car",
    VehicleType.TRUCK_MINI: "Mini Truck",
    VehicleType.TRUCK_LARGE: "Large Truck",
}

MENU_OPTIONS = {
    "1": "Dashboard",
    "2": "List users",
    "3": "Create user",
    "4": "Edit user",
    "5": "Delete user",
    "6": "Park vehicle",
    "7": "Occupied spaces",
    "8": "Find vehicle by plate",
    "9": "Remove vehicle",
    "10": "Show building structures",
    "11": "Switch building",
    "12": "Clear selected building",
    "13": "Seed demo data",
    "14": "Exit",
}


def run_cli():
    ParkingLotCLI().run()


class ParkingLotCLI:
    def __init__(self, console=None):
        self.console = console or Console()
        self.structure_name = None
        self.building = None

    def run(self):
        self.show_welcome()
        self.select_starting_building()

        while True:
            self.show_header()
            self.show_menu()
            choice = Prompt.ask(
                "Choose an option",
                choices=list(MENU_OPTIONS.keys()),
                console=self.console,
            )

            if choice == "1":
                self.show_dashboard()
            elif choice == "2":
                self.show_users()
            elif choice == "3":
                self.create_user_from_input()
            elif choice == "4":
                self.edit_user_from_input()
            elif choice == "5":
                self.delete_user_from_input()
            elif choice == "6":
                self.park_vehicle_from_input()
            elif choice == "7":
                self.show_occupied_spaces()
            elif choice == "8":
                self.find_vehicle_from_input()
            elif choice == "9":
                self.remove_vehicle_from_input()
            elif choice == "10":
                self.show_building_structures()
            elif choice == "11":
                self.switch_building_structure()
            elif choice == "12":
                self.clear_selected_building()
            elif choice == "13":
                self.seed_demo_data_from_input()
            elif choice == "14":
                self.console.print("[bold green]Goodbye.[/bold green]")
                break

    def show_welcome(self):
        self.console.print()
        self.console.print(
            Panel(
                Align.center(
                    "[bold cyan]Parking Lot Manager[/bold cyan]\n"
                    "[white]Choose a building, manage users, and persist parked vehicles.[/white]"
                ),
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    def select_starting_building(self):
        self.console.print("[bold]Select the building to operate on first.[/bold]")
        self.structure_name = self.choose_building_structure(allow_cancel=False)
        self.building = ParkingBuilding(self.structure_name)

    def show_header(self):
        counts = self.building.get_space_counts()
        total = sum(vehicle_counts["total"] for vehicle_counts in counts.values())
        occupied = sum(vehicle_counts["occupied"] for vehicle_counts in counts.values())
        available = sum(vehicle_counts["available"] for vehicle_counts in counts.values())

        header = (
            f"[bold]Building:[/bold] {self.structure_name}    "
            f"[green]Available:[/green] {available}    "
            f"[yellow]Occupied:[/yellow] {occupied}    "
            f"[cyan]Total:[/cyan] {total}"
        )

        self.console.print()
        self.console.print(Panel(header, title="Parking Lot CLI", border_style="cyan"))

    def show_menu(self):
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Option", style="cyan", justify="right")
        table.add_column("Action", style="white")

        for key, label in MENU_OPTIONS.items():
            table.add_row(key, label)

        self.console.print(table)

    def show_dashboard(self):
        self.show_parking_summary()
        self.show_occupied_spaces(limit=10)

    def show_users(self):
        users = load_users()
        self.console.print()

        if not users:
            self.console.print("[yellow]No users found.[/yellow]")
            return

        self.console.print(self.build_users_table(users))

    def create_user_from_input(self):
        self.console.print()
        self.console.print(Panel("Create User", border_style="cyan"))

        while True:
            try:
                user = create_user(
                    self.prompt_required("First name"),
                    self.prompt_required("Last name"),
                    self.prompt_required("Email"),
                    self.prompt_required("Phone"),
                    status=self.prompt_status(default="active"),
                )
            except ValueError as error:
                self.console.print(f"[red]{error}[/red]")
                if not Confirm.ask("Try again?", default=True, console=self.console):
                    return
            else:
                self.console.print(
                    f"[green]Created user {user.get_user_id()}: {user.get_full_name()}[/green]"
                )
                return

    def edit_user_from_input(self):
        users = load_users()
        user = self.choose_user(users)
        if user is None:
            return

        self.console.print("[dim]Press Enter to keep the current value.[/dim]")
        first_name = self.prompt_optional("First name", user.get_first_name())
        last_name = self.prompt_optional("Last name", user.get_last_name())
        email = self.prompt_optional("Email", user.get_email())
        phone = self.prompt_optional("Phone", user.get_phone())
        status = self.prompt_status(default=user.get_status())

        try:
            updated_user = update_user(
                user.get_user_id(),
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                status=status,
            )
        except ValueError as error:
            self.console.print(f"[red]{error}[/red]")
            return

        self.console.print(
            f"[green]Updated user {updated_user.get_user_id()}: "
            f"{updated_user.get_full_name()}[/green]"
        )

    def delete_user_from_input(self):
        users = load_users()
        user = self.choose_user(users)
        if user is None:
            return

        if not Confirm.ask(
            f"Delete {user.get_full_name()} and clear their parked vehicles?",
            default=False,
            console=self.console,
        ):
            self.console.print("[yellow]Delete cancelled.[/yellow]")
            return

        deleted_user = delete_user(user.get_user_id())
        self.building.reload()
        self.console.print(
            f"[green]Deleted {deleted_user.get_full_name()} and cleared their spaces.[/green]"
        )

    def show_building_structures(self):
        table = Table(title="Parking Building Structures", box=box.ROUNDED)
        table.add_column("Option", style="cyan", justify="right")
        table.add_column("Name", style="bold")
        table.add_column("Spaces", justify="right")
        table.add_column("Breakdown")

        for index, name in enumerate(get_structure_names(), start=1):
            counts = count_vehicle_types(PARKING_BUILDING_STRUCTURES[name])
            table.add_row(
                str(index),
                name,
                str(sum(counts.values())),
                self.format_vehicle_type_counts(counts),
            )

        self.console.print()
        self.console.print(table)

    def switch_building_structure(self):
        structure_name = self.choose_building_structure(allow_cancel=True)
        if structure_name is None:
            return

        self.structure_name = structure_name
        self.building = ParkingBuilding(self.structure_name)
        self.console.print(f"[green]Switched to '{self.structure_name}'.[/green]")

    def show_parking_summary(self):
        counts = self.building.get_space_counts()
        table = Table(title="Parking Summary", box=box.ROUNDED)
        table.add_column("Vehicle Type", style="cyan")
        table.add_column("Available", justify="right", style="green")
        table.add_column("Occupied", justify="right", style="yellow")
        table.add_column("Total", justify="right")

        for vehicle_type in VehicleType:
            vehicle_counts = counts[vehicle_type]
            table.add_row(
                VEHICLE_TYPE_LABELS[vehicle_type],
                str(vehicle_counts["available"]),
                str(vehicle_counts["occupied"]),
                str(vehicle_counts["total"]),
            )

        self.console.print()
        self.console.print(table)

    def park_vehicle_from_input(self):
        users = load_users()

        if not users:
            self.console.print("[yellow]No users found. Create a user before parking.[/yellow]")
            return

        user = self.choose_user(users)
        if user is None:
            return

        license_plate = self.prompt_license_plate()
        if license_plate is None:
            return

        vehicle_type = self.choose_vehicle_type()
        if vehicle_type is None:
            return

        try:
            space = self.building.park_vehicle(Vehicle(vehicle_type, user, license_plate))
        except ValueError as error:
            self.console.print(f"[red]{error}[/red]")
            return

        if space is None:
            self.console.print(
                f"[yellow]No available {VEHICLE_TYPE_LABELS[vehicle_type]} spaces "
                f"in {self.structure_name}.[/yellow]"
            )
            return

        self.console.print(
            Panel(
                f"[green]Allocated {space.space_id}[/green]\n"
                f"Vehicle: {VEHICLE_TYPE_LABELS[vehicle_type]}\n"
                f"Plate: {license_plate}\n"
                f"User: {user.get_full_name()}",
                title="Vehicle Parked",
                border_style="green",
            )
        )

    def show_occupied_spaces(self, limit=None):
        occupied_spaces = [
            space for space in self.building.iter_spaces() if not space.is_available()
        ]

        self.console.print()
        if not occupied_spaces:
            self.console.print("[yellow]No occupied spaces.[/yellow]")
            return

        table = Table(title="Occupied Spaces", box=box.ROUNDED)
        table.add_column("Space", style="cyan")
        table.add_column("Vehicle")
        table.add_column("Plate")
        table.add_column("User")
        table.add_column("User ID", justify="right")

        spaces_to_show = occupied_spaces[:limit] if limit is not None else occupied_spaces
        for space in spaces_to_show:
            vehicle = space.parked_vehicle
            user = vehicle.user if vehicle is not None else None
            table.add_row(
                space.space_id,
                VEHICLE_TYPE_LABELS[space.vehicle_type],
                vehicle.license_plate if vehicle is not None else "",
                user.get_full_name() if user is not None else "Unknown user",
                str(user.get_user_id()) if user is not None else "",
            )

        self.console.print(table)

        if limit is not None and len(occupied_spaces) > limit:
            self.console.print(f"[dim]Showing {limit} of {len(occupied_spaces)} occupied spaces.[/dim]")

    def find_vehicle_from_input(self):
        license_plate = self.prompt_license_plate()
        if license_plate is None:
            return

        row = find_vehicle_by_license_plate(license_plate)
        if row is None:
            self.console.print("[yellow]No parked vehicle found for that plate.[/yellow]")
            return

        user = find_user_by_id(row["user_id"]) if row["user_id"] else None
        self.console.print(
            Panel(
                f"Building: {row['building_name']}\n"
                f"Space: {row['space_id']}\n"
                f"Vehicle: {VEHICLE_TYPE_LABELS[VehicleType.from_value(row['vehicle_type'])]}\n"
                f"Plate: {row['license_plate']}\n"
                f"User: {user.get_full_name() if user is not None else 'Unknown user'}",
                title="Vehicle Found",
                border_style="green",
            )
        )

    def remove_vehicle_from_input(self):
        choice = Prompt.ask(
            "Remove by",
            choices=["space", "plate", "cancel"],
            default="space",
            console=self.console,
        )

        if choice == "cancel":
            self.console.print("[yellow]Remove cancelled.[/yellow]")
            return

        if choice == "plate":
            self.remove_vehicle_by_plate_from_input()
            return

        space = self.choose_occupied_space()
        if space is None:
            return

        vehicle = self.building.remove_vehicle_from_space(space.space_id)
        self.print_removed_vehicle(vehicle, space.space_id)

    def remove_vehicle_by_plate_from_input(self):
        license_plate = self.prompt_license_plate()
        if license_plate is None:
            return

        row = find_vehicle_by_license_plate(license_plate)
        if row is None:
            self.console.print("[yellow]No parked vehicle found for that plate.[/yellow]")
            return

        vehicle = remove_vehicle_by_license_plate(license_plate)
        self.building.reload()
        self.print_removed_vehicle(vehicle, row["space_id"])

    def clear_selected_building(self):
        if not Confirm.ask(
            f"Clear all occupied spaces in {self.structure_name}?",
            default=False,
            console=self.console,
        ):
            self.console.print("[yellow]Clear cancelled.[/yellow]")
            return

        cleared_count = clear_building_occupancy(self.structure_name)
        self.building.reload()
        self.console.print(f"[green]Cleared {cleared_count} occupied spaces.[/green]")

    def seed_demo_data_from_input(self):
        if not Confirm.ask(
            "Reset demo users and demo parking occupancy?",
            default=False,
            console=self.console,
        ):
            self.console.print("[yellow]Demo seed cancelled.[/yellow]")
            return

        try:
            result = seed_demo_data()
        except ValueError as error:
            self.console.print(f"[red]{error}[/red]")
            return

        self.building.reload()
        self.console.print(
            f"[green]Seeded {result.users_seeded} demo users and "
            f"{result.occupied_spaces_seeded} occupied spaces.[/green]"
        )

    def choose_building_structure(self, allow_cancel):
        structure_names = get_structure_names()
        self.show_building_structures()

        while True:
            prompt = "Structure name or number"
            if allow_cancel:
                prompt += " (blank to cancel)"

            choice = Prompt.ask(
                prompt,
                default="",
                show_default=False,
                console=self.console,
            ).strip()

            if not choice and allow_cancel:
                self.console.print("[yellow]Structure selection cancelled.[/yellow]")
                return None

            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(structure_names):
                    return structure_names[index]
            elif choice in PARKING_BUILDING_STRUCTURES:
                return choice

            self.console.print("[red]Unknown building structure. Try again.[/red]")

    def choose_user(self, users):
        if not users:
            self.console.print("[yellow]No users found.[/yellow]")
            return None

        self.console.print(self.build_users_table(users))

        while True:
            user_id_input = Prompt.ask(
                "User id (blank to cancel)",
                default="",
                show_default=False,
                console=self.console,
            ).strip()

            if not user_id_input:
                self.console.print("[yellow]User selection cancelled.[/yellow]")
                return None

            if not user_id_input.isdigit():
                self.console.print("[red]User id must be a number.[/red]")
                continue

            user = find_user_by_id(user_id_input, users)
            if user is not None:
                return user

            self.console.print("[red]User not found. Try again.[/red]")

    def choose_vehicle_type(self):
        vehicle_types = list(VehicleType)
        table = Table(title="Vehicle Types", box=box.ROUNDED)
        table.add_column("Option", justify="right", style="cyan")
        table.add_column("Vehicle Type")

        for index, vehicle_type in enumerate(vehicle_types, start=1):
            table.add_row(str(index), VEHICLE_TYPE_LABELS[vehicle_type])

        self.console.print(table)

        while True:
            choice = Prompt.ask(
                "Vehicle type number (blank to cancel)",
                default="",
                show_default=False,
                console=self.console,
            ).strip()

            if not choice:
                self.console.print("[yellow]Vehicle type selection cancelled.[/yellow]")
                return None

            if not choice.isdigit():
                self.console.print("[red]Vehicle type must be a number.[/red]")
                continue

            index = int(choice) - 1
            if 0 <= index < len(vehicle_types):
                return vehicle_types[index]

            self.console.print("[red]Unknown vehicle type. Try again.[/red]")

    def choose_occupied_space(self):
        occupied_spaces = [
            space for space in self.building.iter_spaces() if not space.is_available()
        ]

        if not occupied_spaces:
            self.console.print("[yellow]No occupied spaces.[/yellow]")
            return None

        self.show_occupied_spaces()

        while True:
            space_id = Prompt.ask(
                "Space id (blank to cancel)",
                default="",
                show_default=False,
                console=self.console,
            ).strip()

            if not space_id:
                self.console.print("[yellow]Space selection cancelled.[/yellow]")
                return None

            space = self.building.find_space_by_id(space_id)
            if space is None:
                self.console.print("[red]Unknown parking space. Try again.[/red]")
                continue

            if space.is_available():
                self.console.print(f"[yellow]{space.space_id} is already available.[/yellow]")
                continue

            return space

    def build_users_table(self, users):
        table = Table(title="Users", box=box.ROUNDED)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Name")
        table.add_column("Email")
        table.add_column("Phone")
        table.add_column("Status")

        for user in users:
            table.add_row(
                str(user.get_user_id()),
                user.get_full_name(),
                user.get_email(),
                user.get_phone(),
                user.get_status(),
            )

        return table

    def prompt_required(self, prompt):
        while True:
            value = Prompt.ask(prompt, console=self.console).strip()
            if value:
                return value

            self.console.print("[red]This field is required.[/red]")

    def prompt_optional(self, prompt, current_value):
        value = Prompt.ask(
            f"{prompt} [{current_value}]",
            default="",
            show_default=False,
            console=self.console,
        ).strip()
        return value or current_value

    def prompt_status(self, default):
        return Prompt.ask(
            "Status",
            choices=sorted(VALID_USER_STATUSES),
            default=default,
            console=self.console,
        )

    def prompt_license_plate(self):
        while True:
            value = Prompt.ask(
                "License plate (blank to cancel)",
                default="",
                show_default=False,
                console=self.console,
            ).strip()

            if not value:
                self.console.print("[yellow]License plate entry cancelled.[/yellow]")
                return None

            try:
                return validate_license_plate(value)
            except ValueError as error:
                self.console.print(f"[red]{error}[/red]")

    def print_removed_vehicle(self, vehicle, space_id):
        if vehicle is None:
            self.console.print("[yellow]No parked vehicle found to remove.[/yellow]")
            return

        user = vehicle.user
        self.console.print(
            f"[green]Removed {VEHICLE_TYPE_LABELS[vehicle.vehicle_type]} "
            f"{vehicle.license_plate} from {space_id}"
            f"{' for ' + user.get_full_name() if user is not None else ''}.[/green]"
        )

    def format_vehicle_type_counts(self, counts):
        parts = []

        for vehicle_type in VehicleType:
            count = counts.get(vehicle_type, 0)
            if count:
                parts.append(f"{count} {VEHICLE_TYPE_LABELS[vehicle_type]}")

        return ", ".join(parts)
