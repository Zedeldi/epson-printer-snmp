## Adding models to `epson-printer-snmp`

### WICReset

The first thing you want to do is install [WICReset](https://wic-reset.com) and reset the waste ink counter with the `trial` key, only one use per printer.
It will reset the printer counter from 100% to 80% and we want the 0%.
Once you successfully reset your printer counter to 80%, go to `%APPDATA%\wicreset\application.log` on Windows or `~/.wicreset/application.log` on Linux-based systems.

### Using `wicreset.py`

`wicreset.py` will parse a WICReset log file and try to get the values for your printer.

To do this, run `python wicreset.py --json <path to log>`, which will give you a model that you can add to `models.json`.

If the structure is different to other printer models, this may fail and you'll need to [look through the logs manually](#manual).

### Manual

In `application.log`, you have to search for something similar to this (in this case we are using the Epson XP-700 Series): `RemoteControl::RESET_GUID RESET GUID: XP-700 Series 1061 KEY`.
Just below this line, you should see a series of hexadecimal numbers.
We're interested in the hexadecimal numbers with `REAL` at the end of each line.
It should look like this: `7C 7C 10 00 28 00 42 BD 21 10 00 68 49 6A 63 6A 74 64 76 74`.
Now we convert every single one of them to a decimal and then add dots between numbers.

#### Code Snippet for converting the hex string into the required decimal format
```python
hex_string = input("Enter a hex string: ")
hex_list = hex_string.split(" ")  # Split string into a list
decimal_list = [int(hex_num, 16) for hex_num in hex_list]  # Convert each hex to decimal
decimal_string = ".".join(map(str, decimal_list))
print(f"Decimal format: {decimal_string}")
```

They should look like this: `124.124.16.0.40.0.66.189.33.16.0.104.73.106.99.106.116.100.118.116`.
Do this with every single one of them; there's about 10.

Once you have the converted lines, you will see that they have a format:
`{eeprom_link}.124.124.16.0.{password}.66.189.33.{oid}.0.{value}.{eeprom_write}`.
`eeprom_link` is always `1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1`.
The password is the two numbers next to `124.124.16.0.` in this case is `40` and `0`.
Then, we have the `66.189.33` and the `oid` (`16`) with a `value` (`104`) and the `eeprom_write` (`73.106.99.106.116.100.118.116`).

### Model

To create our model, start with the following template:
```
"EPSON YOURMODEL": {
    "password": [, ],
    "eeprom_link": "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1",
    "eeprom_write": "",
    "ink_levels": {},
    "waste_inks": [
      {"oids": [, ], "total": },
      {"oids": [, ], "total": },
      {"oids": [, ], "total": }
    ],
    "maintenance_levels": [, ],
    "unknown_oids": []
  }
```

### Waste Ink

We need to calculate the totals for the waste ink counters.

One of the OIDs and values looks like this: `16.0.104` for the Epson XP-700, so the OID is 16 with a value of 104.
If we do that with every single of them:
```
16 = 104 (group #1)
17 = 26 (group #1)
6 = 0 (unknown)
52 = 94 (maintenance #1)
20 = 0 (group #3)
21 = 0 (group #3)
18 = 18 (group #2)
19 = 9 (group #2)
6 = 0 (unknown)
53 = 94 (maintenance #2)
237.1.0 (unknown format)
```

To group the waste ink counters requires a bit of guessing.
They tend to be consecutive and in pairs, such as (16, 17), (18, 19) and (20, 21).
Some models have an extra value for some counters, which is usually set to 0 by WICReset during the 80% trial reset.

Now we need to convert the value of group #1 in hexadecimal.
In this case, `104 = 0x68` and `26 = 0x1A`.
Then, we need to concatenate them in reverse, like this: `0x1A68` = `6760.0` in decimal.
After using WICReset with the trial key, we know the percentage is 80%.
So, we take the value after concatenating the two hex values in reverse and use that to find the total:
`(6760 / 80) * 100 = 8450.0`

### Other Values

Maintenance levels are always set to `94`, so the OIDs with value `94` are for maintenance.

All other OIDs (not waste ink or maintenance) are unknown.

### Result

After putting everything together, we have this:
```
"EPSON XP-700": {
    "password": [40, 0],
    "eeprom_link": "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1",
    "eeprom_write": "73.106.99.106.116.100.118.116",
    "ink_levels": {},
    "waste_inks": [
      {"oids": [16, 17], "total": 8450.0},
      {"oids": [18, 19], "total": 2902.5},
      {"oids": [20, 21], "total": null}
    ],
    "maintenance_levels": [52, 53],
    "unknown_oids": [6, 237]
  }
```

Guide made by [@j6ta](https://github.com/Zxuus) :)
