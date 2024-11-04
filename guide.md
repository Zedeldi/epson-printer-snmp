## How to make your Epson printer compatible with epson-printer-snmp

The first thing you want to do is install [WicReset](https://wic-reset.com>) and reset the waste ink counter with the **trial** key, only one use per printer. It will reset the printer counter from 100% to 80% and we want the 0%. Once you successfully reset your printer counter to 80%, go to `%APPDATA%\wicreset\application.log` on Windows or `~/.wicreset/application.log` on Linux-based systems. On the `application.log` you have to search for something similar to this (in this case we are using the Epson XP-700 Series): `RemoteControl::RESET_GUID RESET GUID: XP-700 Series 1061 KEY`. Just below this line, you should see a series of hexadecimal numbers. We're interested in the hexadecimal numbers next to the `REAL` thing. It should look like this: `7C 7C 10 00 28 00 42 BD 21 10 00 68 49 6A 63 6A 74 64 76 74`. Now we convert every single one of them to a decimal and then add dots between numbers. They should look like this: `124.124.16.0.40.0.66.189.33.16.0.104.73.106.99.106.116.100.118.116`. Do this with every single one of them, they're about 10.

Once you have the 10 hexadecimal to decimals you will see that they have a format, `{eeprom_link}.124.124.16.0.{password}.66.189.33.{oid}.0.{value}.{eeprom_write}`, **eeprom_link** is always `1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1` then the password is the two numbers next to `124.124.16.0.` in this case is **40 and 0**  then we have the `66.189.33` and then the **oid** (16) with a **value** (104) and the **eeprom_write** `73.106.99.106.116.100.118.116`.

We need to create our model so lets create the strocture for it: 
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
We need to calculate the total of both oids.

One of the oid and value looks like this: `16.0.104` for the Epson XP-700 so the oid is 16 with a value of 104. If we do that with every single of them:
```
16 = 104 (group #1) 
17 = 26 (group #1)
6 = 0 (uknown)
52 = 94 (manteinance #1)
20 = 0 (group #3)
21 = 0 (group #3)
18 = 18 (group #2) 
19 = 9 (group #2)
6 = 0 (uknown)
53 = 94 (manteinance #2)
237.1.0 (unknown weird case) 
```
Now we need to conver the value of group 1 in hexadecimal, this **case 104 = 0x68** and **26 = 0x1A** now we need to concatenate them like this: `0x1A68` thats the total so is **6760.0**.

Manteinance level is 94 so the oids with value 94 are mantenance. 

To make the groups it's abit of guessing, they tend to be consecutive and in pairs, hence (16, 17), (18, 19) and (20, 21)
The models with an extra counter is usually set to 0 by WICReset during the 80% trial reset.

And now we can put everything together and we have this:
```
"EPSON XP-700": {
    "password": [40, 0],
    "eeprom_link": "1.3.6.1.4.1.1248.1.2.2.44.1.1.2.1",
    "eeprom_write": "73.106.99.106.116.100.118.116",
    "ink_levels": {},
    "waste_inks": [
      {"oids": [16, 17], "total": 6760.0},
      {"oids": [18, 19], "total": 390.0},
      {"oids": [20, 21], "total": null}
    ],
    "maintenance_levels": [52, 53],
    "unknown_oids": [6, 237]
  }
```


Guide made by [@j6ta](https://github.com/Zxuus) :)
