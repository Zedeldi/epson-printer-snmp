"""
SNMP handler for Epson printers.

Based on https://github.com/gentu/reink-net/blob/master/reink-net.rb
Modified for the EPSON WF-7525 Series
"""

import itertools
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import easysnmp


@dataclass
class Printer:
    """Dataclass to store information about a printer."""

    hostname: str
    password: list[int] = field(default_factory=lambda: [101, 0])
    eeprom_link: str = "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1"
    ink_levels: dict = field(
        default_factory=lambda: {
            "black": 0x1C,
            "magenta": 0x1F,
            "yellow": 0x22,
            "cyan": 0x25,
        }
    )
    waste_inks: list[dict] = field(
        default_factory=lambda: [
            {"oids": [20, 21], "total": 19650},
            {"oids": [22, 23], "total": 5205},
        ]
    )

    def __post_init__(self) -> None:
        """Initialise printer instance."""
        self.session = Session(printer=self)

    @property
    def stats(self) -> dict[str, Any]:
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
        self, printer: Printer, community: str = "public", version: int = 1
    ) -> None:
        """Initialise session."""
        self.printer = printer
        super().__init__(
            hostname=self.printer.hostname, community=community, version=version
        )

    def get_value(self, oids: str) -> str:
        """Return value of OIDs."""
        return self.get(oids).value

    def get_read_eeprom_oid(self, oid: int) -> str:
        """Return address for reading from EEPROM for specified OID."""
        return (
            f"{self.printer.eeprom_link}"
            ".124.124.7.0"
            f".{self.printer.password[0]}"
            f".{self.printer.password[1]}"
            ".65.190.160"
            f".{oid}.0"
        )

    def get_write_eeprom_oid(self, oid: int, value: Any) -> str:
        """Return address for writing to EEPROM for specified OID."""
        return (
            f"{self.printer.eeprom_link}"
            ".124.124.16.0"
            f".{self.printer.password[0]}"
            f".{self.printer.password[1]}"
            ".66.189.33"
            f".{oid}.0.{value}"
            ".84.98.116.98.111.114.118.98"
        )

    def read_eeprom(self, oid: int) -> str:
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

    def read_eeprom_many(self, oids: list[int]) -> list[str]:
        """Read EEPROM data with multiple values."""
        return [self.read_eeprom(oid) for oid in oids]

    def write_eeprom(self, oid: int, value: int) -> None:
        """Write value to OID with specified type to EEPROM."""
        self.get(self.get_write_eeprom_oid(oid, value))

    def dump_eeprom(self, start: int = 0, end: int = 0xFF) -> dict[int, int]:
        """Dump EEPROM data from start to end."""
        d = {}
        for oid in range(start, end):
            d[oid] = int(self.read_eeprom(oid), 16)
        return d

    def get_model(self) -> str:
        """Return model of printer."""
        return self.get_value("1.3.6.1.2.1.1.5.0")

    def get_model_full(self) -> str:
        """Return full model of printer."""
        return self.get_value("1.3.6.1.2.1.25.3.2.1.3.1")

    def get_serial_number(self) -> str:
        """Return serial number of printer."""
        return "".join(
            chr(int(value, 16))
            for value in self.read_eeprom_many(
                [192, 193, 194, 195, 196, 197, 198, 199, 200, 201]
            )
        )

    def get_eeps2_version(self) -> str:
        """Return EEPS2 version."""
        return self.get_value("1.3.6.1.2.1.2.2.1.2.1")

    def get_ink_levels(self) -> dict[str, int]:
        """Return ink levels of printer."""
        result = self.get_value(f"{self.printer.eeprom_link}.115.116.1.0.1")
        d = {
            colour: ord(result[idx]) for colour, idx in self.printer.ink_levels.items()
        }
        return d

    def get_waste_ink_levels(self) -> list[float]:
        """Return waste ink levels as a percentage."""
        results = []
        for waste_ink in self.printer.waste_inks:
            level = self.read_eeprom_many(waste_ink["oids"])
            level_b10 = int("".join(reversed(level)), 16)
            results.append(round((level_b10 / waste_ink["total"]) * 100, 2))
        return results

    def reset_waste_ink_levels(self) -> None:
        """
        Set waste ink levels to 0.

        hex(int((80 / 100) * 19650)) == 0x3d68
        hex(104), hex(61) = (0x68, 0x3d)
        """
        data = {20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 25: 0, 59: 0, 60: 94, 61: 94}
        for oid, value in data.items():
            self.write_eeprom(oid, value)

    def brute_force(
        self, minimum: int = 0x00, maximum: int = 0xFF
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
        print(f"Usage: {fn} <IP address of printer>")
        sys.exit(1)
    printer = Printer(args[0])
    session = Session(printer)
    pprint(printer.stats)
