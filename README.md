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

Values for waste ink levels are stored in two addresses, which, when reversed, combine to make a value in hex.
This value is then divided by a constant, which again seems to vary across models of printer, to make the percentage.
The constant value can be found by using `wicreset` to read the counters' percentage, getting the hex values of these OIDs, then following the above process to solve:
e.g.
```
# Percentage is 80%.
# Hex values are (0x68, 0x3d) => 0x3d68

(0x3d68 / 80) * 100 = 19650.0
```
Please note that different counters for the same printer may use different constants.

## Libraries

- [easysnmp](https://pypi.org/project/easysnmp/) - SNMP

## Resources

reink-net = <https://github.com/gentu/reink-net>
  - Used as a starting point to create this Python implementation and translated for different model of printer

epson-l4160-ink-waste-resetter = <https://github.com/nicootto/epson-l4160-ink-waste-resetter>

wicreset = <https://wic-reset.com> / <https://www.2manuals.com> / <https://resetters.com>
  - The key, `trial`, can be used to reset your counters to 80%. After packet sniffing with `wireshark`, the correct OIDs can be found
  - This application also stores a log containing SNMP information at `~/.wicreset/application.log`

## License

epson-printer-snmp is licensed under the GPL v3 for everyone to use, modify and share freely.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

[![GPL v3 Logo](https://www.gnu.org/graphics/gplv3-127x51.png)](https://www.gnu.org/licenses/gpl-3.0-standalone.html)

## Donate

If you found this project useful, please consider donating. Any amount is greatly appreciated! Thank you :smiley:

[![PayPal](https://www.paypalobjects.com/webstatic/mktg/Logo/pp-logo-150px.png)](https://paypal.me/ZackDidcott)

My bitcoin address is: [bc1q5aygkqypxuw7cjg062tnh56sd0mxt0zd5md536](bitcoin://bc1q5aygkqypxuw7cjg062tnh56sd0mxt0zd5md536)
