# epson-printer-snmp

[![GitHub license](https://img.shields.io/github/license/Zedeldi/epson-printer-snmp?style=flat-square)](https://github.com/Zedeldi/epson-printer-snmp/blob/master/LICENSE) [![GitHub last commit](https://img.shields.io/github/last-commit/Zedeldi/epson-printer-snmp?style=flat-square)](https://github.com/Zedeldi/epson-printer-snmp/commits) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

Read information and reset waste ink counters on Epson printers, using SNMP.

## Description

This project was designed for a EPSON WF-7525 Series printer, but inspired by [projects](#resources) for other models.
Hopefully, releasing this code will help save a printer from the trash and improve consumer repairability for these devices.
Information about specific models is stored in `models.json`, as a dictionary.
Feel free to raise an issue/pull request for adding support for another model of printer, with logs from `wicreset` or similar attached.

The format for reading values is:

`{eeprom_link}.124.124.7.0.{password}.65.190.160.{oid}.0`

The format for setting values is:

`{eeprom_link}.124.124.16.0.{password}.66.189.33.{oid}.0.{value}.{eeprom_write}`

Where `eeprom_link` is consistently `1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1` and `password` is two values, e.g. `101.0`. `password` and `eeprom_write` seem to vary between different models of printer. This can be found by using a tool, such as `wicreset`, and checking the request it sends.
A method for brute forcing the password is provided in `Session.brute_force`, which tries to get a value from the EEPROM, for every permutation of `[0x00, 0x00]` to `[0xFF, 0xFF]`.

Setting values is done by *getting* an address, where the OID and value to set is specified in the query.
Certain values of these formats also vary between models of printer.

Various methods are defined to get specific information.
The `Printer.stats` method will return a dictionary of most useful information.

Values for waste ink levels are stored across multiple addresses, which, when reversed, combine to make a value in hex.
This value is then divided by a constant, which again seems to vary across models of printer, to make the percentage.
The constant value can be found by using `wicreset` to read the counters' percentage, getting the hex values of these OIDs, then following the above process to solve:
e.g.
```
# Percentage is 80%.
# Hex values are (0x68, 0x3d) => 0x3d68

(0x3d68 / 80) * 100 = 19650.0
```
Please note that different counters for the same printer may use different constants.

Courtesy of [@PeaShooterR](https://github.com/PeaShooterR), some models of printers seem to store waste ink counters in a slightly different way, across three counters instead of two (see issue [#1](https://github.com/Zedeldi/epson-printer-snmp/issues/1)).

To compare, `wicreset` writes the following values for the specified model of printer:

<table>
<tr><th>WF-7525</th><th>PX-047A</th></tr>
<tr><td>

| OID | Value | Usage               |
|-----|-------|---------------------|
| 20  | 104   | Counter 1 (shown)   |
| 21  | 61    | Counter 1 (shown)   |
| 22  | 68    | Counter 2 (shown)   |
| 23  | 16    | Counter 2 (shown)   |
| 24  | 0     | Counter 1 (real)    |
| 25  | 0     | Counter 1 (real)    |
| 59  | 0     | Unknown             |
| 60  | 94    | Maintenance level 1 |
| 61  | 94    | Maintenance level 2 |

</td><td>

| OID | Value | Usage               |
|-----|-------|---------------------|
| 24  | 120   | Counter 1 (shown)   |
| 25  | 12    | Counter 1 (shown)   |
| 26  | 44    | Counter 2 (shown)   |
| 27  | 10    | Counter 2 (shown)   |
| 30  | 0     | Counter 1 (shown)   |
| 28  | 0     | Counter 1 (real)    |
| 29  | 0     | Counter 1 (real)    |
| 34  | 0     | Counter 2 (shown)   |
| 46  | 94    | Maintenance level 1 |
| 47  | 94    | Maintenance level 2 |
| 49  | 0     | Unknown             |

</td></tr> </table>

> Whenever a print job is received, the printer will compare the REAL data and the SHOWN data, then updates SHOWN data to the larger value.
> After performing operations such as head cleaning that increase the counter, the printer increments the SHOWN data and saves it to both (24, 25, 30) and (28, 29).

### Supported models

| Tested     | Not tested |
| ---------- | ---------- |
| XP-700     | ET-2550    |
| XP-540     | ET-2700    |
| WF-7525    | L366       |
| ET-2756    |            |

### WICReset

> The WICReset utility and “key” allow end-users to reset the waste ink counter in their printer to clear errors related to waste ink (eg: “Parts inside your printer have reached the end of their service life”).

The key, `trial`, can be used to reset your counters to 80% for free. After packet sniffing with `wireshark`, the correct OIDs can be found.

The application also stores a log containing SNMP information at `~/.wicreset/application.log` on Linux-based systems, or `%APPDATA%\wicreset\application.log` on Windows.

Once the log has been found, you can use `wicreset.py <path to log>` to automatically parse and guess the OID structure of your printer.

If the structure is similar to other printers and the results look sane, please add the model to `models.json` and submit a pull request.

## Usage

Run: `python main.py` (interactive) or `python main.py [host] [model ...]` (command-line arguments)

See `python main.py --help` for more information.

Parse WICReset logs: `wicreset.py <path to log>`

### Docker

A minimal Dockerfile is provided to easily build an image with the relevant `net-snmp` packages installed.

Build: `docker build -t "epson-printer-snmp" .`

Run: `docker run -it --rm "epson-printer-snmp"`

## Libraries

- [easysnmp](https://pypi.org/project/easysnmp/) - SNMP

## Resources

reink-net = <https://github.com/gentu/reink-net>
  - Used as a starting point to create this Python implementation and translated for a different model of printer

epson-l4160-ink-waste-resetter = <https://github.com/nicootto/epson-l4160-ink-waste-resetter>

epson_print_conf = <https://github.com/Ircama/epson_print_conf>

wicreset = <https://wic-reset.com> / <https://www.2manuals.com> / <https://resetters.com>

## License

epson-printer-snmp is licensed under the GPL v3 for everyone to use, modify and share freely.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

[![GPL v3 Logo](https://www.gnu.org/graphics/gplv3-127x51.png)](https://www.gnu.org/licenses/gpl-3.0-standalone.html)

## Donate

If you found this project useful, please consider donating. Any amount is greatly appreciated! Thank you :smiley:

[![PayPal](https://www.paypalobjects.com/webstatic/mktg/Logo/pp-logo-150px.png)](https://paypal.me/ZackDidcott)

My bitcoin address is: [bc1q5aygkqypxuw7cjg062tnh56sd0mxt0zd5md536](bitcoin://bc1q5aygkqypxuw7cjg062tnh56sd0mxt0zd5md536)
