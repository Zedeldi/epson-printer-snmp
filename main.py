"""
SNMP handler for Epson printers.

Based on https://github.com/gentu/reink-net/blob/master/reink-net.rb
Originally modified for the EPSON WF-7525 Series.
"""

import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Type

import easysnmp


class Model:
    """Class to handle known printer models."""

    JSON_PATH = Path(__file__).absolute().parent / "models.json"

    @classmethod
    def get_all(cls: Type["Model"]) -> dict:
        """Return dictionary of all known models."""
        with open(cls.JSON_PATH, "r") as fd:
            return json.load(fd)

    @classmethod
    def get(cls: Type["Model"], model: str) -> dict:
        """Return dictionary for specified model."""
        models = cls.get_all()
        try:
            return models[model]
        except KeyError as err:
            raise KeyError(f"Model '{model}' not found.") from err

    @classmethod
    def select(cls: Type["Model"]) -> str:
        """Interactively select a model from the list."""
        models = sorted(list(cls.get_all().keys()), key=str.lower)
        for idx, name in enumerate(models):
            print(f"{idx}: {name}")
        select_idx = int(input("Select model: "))
        return models[select_idx]


@dataclass
class Printer:
    """Dataclass to store information about a printer."""

    hostname: str
    password: list[int]
    eeprom_link: str
    eeprom_write: str
    ink_levels: dict[str, int]
    waste_inks: list[dict]
    maintenance_levels: list[int]
    unknown_oids: list[int]

    def __post_init__(self: "Printer") -> None:
        """Initialise printer instance with a session."""
        self.session = Session(printer=self)

    @classmethod
    def from_model(cls: Type["Printer"], hostname: str, model: str) -> "Printer":
        """Return printer instance from known models in path."""
        return cls(hostname=hostname, **Model.get(model))

    @property
    def stats(self: "Printer") -> dict[str, Any]:
        """Return information about the printer."""
        methods = [
            "get_model_full",
            "get_serial_number",
            "get_eeps2_version",
            "get_ink_levels",
            "get_waste_ink_levels",
        ]
        return {
            method[4:]: self.session.__getattribute__(method)() for method in methods
        }


class Session(easysnmp.Session):
    """SNMP session wrapper."""

    def __init__(
        self: "Session", printer: Printer, community: str = "public", version: int = 1
    ) -> None:
        """Initialise session."""
        self.printer = printer
        super().__init__(
            hostname=self.printer.hostname, community=community, version=version
        )

    def get_value(self: "Session", oids: str) -> str:
        """Return value of OIDs."""
        return self.get(oids).value

    def get_read_eeprom_oid(self: "Session", oid: int) -> str:
        """Return address for reading from EEPROM for specified OID."""
        return (
            f"{self.printer.eeprom_link}"
            ".124.124.7.0"
            f".{self.printer.password[0]}"
            f".{self.printer.password[1]}"
            ".65.190.160"
            f".{oid}.0"
        )

    def get_write_eeprom_oid(self: "Session", oid: int, value: Any) -> str:
        """Return address for writing to EEPROM for specified OID."""
        return (
            f"{self.printer.eeprom_link}"
            ".124.124.16.0"
            f".{self.printer.password[0]}"
            f".{self.printer.password[1]}"
            ".66.189.33"
            f".{oid}.0.{value}"
            f".{self.printer.eeprom_write}"
        )

    def read_eeprom(self: "Session", oid: int) -> str:
        """Read EEPROM data."""
        response = self.get_value(self.get_read_eeprom_oid(oid))
        response = re.findall(r"EE:[0-9A-F]{6}", response)[0][3:]
        chk_addr = response[2:4]
        value = response[4:6]
        if int(chk_addr, 16) != oid:
            raise ValueError(
                f"Address and response address are not equal: {oid} != {chk_addr}"
            )
        return value

    def read_eeprom_many(self: "Session", oids: list[int]) -> list[str]:
        """Read EEPROM data with multiple values."""
        return [self.read_eeprom(oid) for oid in oids]

    def write_eeprom(self: "Session", oid: int, value: int) -> None:
        """Write value to OID with specified type to EEPROM."""
        self.get(self.get_write_eeprom_oid(oid, value))

    def dump_eeprom(self: "Session", start: int = 0, end: int = 0xFF) -> dict[int, int]:
        """Dump EEPROM data from start to end."""
        return {oid: int(self.read_eeprom(oid), 16) for oid in range(start, end)}

    def get_model(self: "Session") -> str:
        """Return model of printer."""
        return self.get_value("1.3.6.1.2.1.1.5.0")

    def get_model_full(self: "Session") -> str:
        """Return full model of printer."""
        return self.get_value("1.3.6.1.2.1.25.3.2.1.3.1")

    def get_serial_number(self: "Session") -> str:
        """Return serial number of printer."""
        return "".join(
            chr(int(value, 16))
            for value in self.read_eeprom_many(
                [192, 193, 194, 195, 196, 197, 198, 199, 200, 201]
            )
        )

    def get_eeps2_version(self: "Session") -> str:
        """Return EEPS2 version."""
        return self.get_value("1.3.6.1.2.1.2.2.1.2.1")

    def get_ink_levels(self: "Session") -> dict[str, int]:
        """Return ink levels of printer."""
        result = self.get_value(f"{self.printer.eeprom_link}.115.116.1.0.1")
        return {
            colour: ord(result[idx]) for colour, idx in self.printer.ink_levels.items()
        }

    def get_waste_ink_levels(self: "Session") -> list[float]:
        """Return waste ink levels as a percentage."""
        results = []
        for waste_ink in self.printer.waste_inks:
            if waste_ink["total"] is None:
                continue
            level = self.read_eeprom_many(waste_ink["oids"])
            level_b10 = int("".join(reversed(level)), 16)
            results.append(round((level_b10 / waste_ink["total"]) * 100, 2))
        return results

    def reset_waste_ink_levels(self: "Session") -> None:
        """
        Set waste ink levels to 0.

        hex(int((80 / 100) * 19650)) == 0x3d68
        hex(104), hex(61) = (0x68, 0x3d)
        """
        waste_inks = {
            oid: 0 for waste_ink in self.printer.waste_inks for oid in waste_ink["oids"]
        }
        maintenance_levels = {
            maintenance_level: 94
            for maintenance_level in self.printer.maintenance_levels
        }
        data = {unknown_oid: 0 for unknown_oid in self.printer.unknown_oids}
        data.update(waste_inks)
        data.update(maintenance_levels)
        for oid, value in data.items():
            self.write_eeprom(oid, value)

    def brute_force(
        self: "Session", minimum: int = 0x00, maximum: int = 0xFF
    ) -> Optional[list[int]]:
        """Brute force password for printer."""
        for x, y in itertools.permutations(range(minimum, maximum), r=2):
            self.printer.password = [x, y]
            print(f"Trying {self.printer.password}...")
            try:
                self.read_eeprom(0x00)
                print(f"Password found: {self.printer.password}")
                return self.printer.password
            except IndexError:
                continue
        return None


if __name__ == "__main__":
    import sys
    from pprint import pprint

    fn, *args = sys.argv
    if not args:
        host = input("IP address of printer: ")
        model = Model.select()
    elif args[0].lower() in ("-h", "--help") or len(args) < 2:
        models = list(Model.get_all().keys())
        print(f"Usage: {fn} <IP address of printer> <model of printer>")
        print(f"Supported models: {models}")
        sys.exit(1)
    else:
        host = args[0]
        model = " ".join(args[1:])
    printer = Printer.from_model(host, model)
    session = Session(printer)
    pprint(printer.stats)
