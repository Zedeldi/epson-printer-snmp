"""Parse WICReset application logs to obtain model OID structure."""

import argparse
import itertools
import json
import re
from pathlib import Path
from pprint import pprint

EEPROM_LINK = "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1"
WRITE_PREFIX = "124.124.16.0."
WRITE_MIDDLE = ".66.189.33."
PASSWORD_LENGTH = 2
EEPROM_WRITE_LENGTH = 8


class WicresetLog:
    """Class to handle parsing WICReset application logs."""

    def __init__(self, path: str | Path) -> None:
        """Initialise instance with path to log."""
        self.path = path
        with open(self.path) as log:
            self.content = log.read()

    def get_model(self) -> str:
        """Return model from log."""
        return re.search("RESET_GUID RESET GUID: (.*) [0-9]* KEY", self.content).group(1)

    def _get_waste_ink_reset_section(self) -> list[str]:
        """Return section for waste ink counter reset."""
        return re.search(
            r"Reset started\. Do not turn off the printer(?:(?!The input key does not exist).)+Reset complete",
            self.content,
            re.DOTALL,
        )[0].splitlines()[1:-1]

    def get_waste_ink_reset_writes_as_hex(self) -> list[str]:
        """Return list of lines for actual writes during reset as hex."""
        oids = []
        section = self._get_waste_ink_reset_section()
        for line in section:
            match = re.search(r".*RESET_DATA RESET DATA: [0-9]* -\s*.*", line)
            if not match:
                continue
            oids.append(match[0].split("-")[1].replace("REAL", "").strip())
        return oids

    def get_waste_ink_reset_writes(self) -> list[str]:
        """Return list of OIDs for actual writes during reset."""
        return [
            self.convert_hex_to_oid(line)
            for line in self.get_waste_ink_reset_writes_as_hex()
        ]

    def get_eeprom_write(self) -> list[str]:
        """Return list for eeprom_write section of OID."""
        write = self.get_waste_ink_reset_writes()[0].split(".")
        return write[-EEPROM_WRITE_LENGTH:]

    def get_password(self) -> tuple[int, int]:
        """Return tuple for printer password."""
        password = (
            self.get_waste_ink_reset_writes()[0]
            .removeprefix(WRITE_PREFIX)
            .split(".")[:PASSWORD_LENGTH]
        )
        return tuple(int(part) for part in password)

    def get_waste_ink_reset_values_as_dict(self) -> dict[int, int]:
        """
        Return dictionary of OIDs to values set during counter reset.

        The format for setting values is:
        {eeprom_link}.124.124.16.0.{password}.66.189.33.{oid}.0.{value}.{eeprom_write}
        """
        values = {}
        writes = self.get_waste_ink_reset_writes()
        for write in writes:
            write = write.removeprefix(
                f"{WRITE_PREFIX}{self.convert_list_to_oid(self.get_password())}{WRITE_MIDDLE}"
            ).removesuffix(f".{self.convert_list_to_oid(self.get_eeprom_write())}")
            write = write.split(".")
            try:
                write = ((int(write[0]), int(write[2])),)
            except IndexError:
                continue
            values.update(dict(write))
        return values

    def get_waste_ink_groups(self) -> list[list[int]]:
        """Return nested lists of grouped OIDs for waste ink counters."""
        writes = self.get_waste_ink_reset_values_as_dict()
        for maintenance_level in self.get_maintenance_levels():
            writes.pop(maintenance_level)
        oids = self.get_consecutive_values(writes.keys())
        return [group for group in oids if len(group) > 1]

    def get_waste_ink_totals(
        self, percentage: int = 80
    ) -> dict[tuple[int], int | None]:
        """Return tuple of waste ink counter totals."""
        groups = self.get_waste_ink_groups()
        writes = self.get_waste_ink_reset_values_as_dict()
        totals = {}
        if len(groups) != 3 or any(len(group) > 2 for group in groups):
            raise ValueError("Unknown structure of waste ink counters")
        for group in groups:
            hex_str = ""
            for oid in reversed(group):
                hex_str += f"{writes[oid]:02x}"
            value = int(hex_str, 16)
            total = (value / percentage) * 100
            if total == 0:
                total = None
            totals[tuple(group)] = total
        return totals

    def get_maintenance_levels(self) -> tuple[int, int]:
        """Return OIDs where maintenance levels are stored."""
        return tuple(
            oid
            for oid, value in self.get_waste_ink_reset_values_as_dict().items()
            if value == 94
        )

    def get_unknown_oids(self) -> tuple[int, ...]:
        """Return tuple of unknown OIDs."""
        writes = self.get_waste_ink_reset_values_as_dict()
        known_oids = list(self.get_maintenance_levels()) + [
            oid for group in self.get_waste_ink_groups() for oid in group
        ]
        for known_oid in known_oids:
            writes.pop(known_oid)
        return tuple(writes.keys())

    def to_dict(self) -> dict:
        """Return dictionary for model structure."""
        waste_inks = [
            {"oids": list(oids), "total": total}
            for oids, total in self.get_waste_ink_totals().items()
        ]
        return {
            self.get_model(): {
                "password": self.get_password(),
                "eeprom_link": EEPROM_LINK,
                "eeprom_write": self.convert_list_to_oid(self.get_eeprom_write()),
                "ink_levels": {},  # not implemented
                "waste_inks": waste_inks,
                "maintenance_levels": self.get_maintenance_levels(),
                "unknown_oids": self.get_unknown_oids(),
            }
        }

    def to_json(self) -> str:
        """Return JSON representation for model structure."""
        return json.dumps(self.to_dict())

    @staticmethod
    def convert_hex_to_oid(oid: str) -> str:
        """Convert hexadecimal string to OID format."""
        return ".".join(str(int(part, 16)) for part in oid.split())

    @staticmethod
    def convert_list_to_oid(oid: list[int]) -> str:
        """Convert list of strings to OID format."""
        return ".".join(str(part) for part in oid)

    @staticmethod
    def get_consecutive_values(values: list[int]) -> list[list[int]]:
        """Return groups of consecutive values from list."""
        return [
            [value[1] for value in group]
            for _, group in itertools.groupby(
                enumerate(values), lambda element: element[0] - element[1]
            )
        ]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments and return Namespace instance."""
    parser = argparse.ArgumentParser(description="Parse WICReset application logs.")
    parser.add_argument("path", help="path to log")
    parser.add_argument(
        "--json", "-j", action="store_true", help="output model as JSON"
    )
    args = parser.parse_args()
    return args


def main() -> None:
    """Output information from WICReset application log."""
    args = parse_args()
    log = WicresetLog(args.path)
    if args.json:
        print(log.to_json())
    else:
        pprint(log.to_dict())


if __name__ == "__main__":
    main()
