# broadlink-bridge

A HTTP/MQTT/LIRC bridge to Broadlink IR/RF devices, written in Python
and powered by [python-broadlink](https://github.com/mjg59/python-broadlink).

🛑 🚧 EXPERIMENTAL / WORK IN PROGRESS 🚧 🛑

## Features

- supports [HTTP](#http) protocol
- supports [MQTT](#mqtt) protocol
- supports [LIRC](#lirc) protocol
- supports multiple Broadlink devices
- supports Broadlink IR/RF codes
- supports Pronto hex codes
- supports defining named commands
- supports specifying repeats
- can act as sending hardware for [IrScrutinizer](http://www.harctoolbox.org/IrScrutinizer.html) via the [LIRC output](http://www.harctoolbox.org/IrScrutinizer.html#The+%22Lirc%22+pane)

## Installing/running

To install: `pip install [--user] git+https://github.com/lbschenkel/broadlink-bridge.git`

To run: `broadlink-bridge [config-file]`

### Docker

(to be written)

### Usage in Home Assistant

This bridge is available as an [unnoficial add-on](https://github.com/lbschenkel/hass-addon-broadlink-bridge/tree/master/broadlink-bridge).

As a [RESTful switch](https://www.home-assistant.io/components/switch.rest):

```yaml
switch:
- platform: rest
  resource: http://BRIDGE_HOST:PORT/device/DEVICE
  body_on: CODE
  body_off: CODE
```

As a [MQTT switch](https://www.home-assistant.io/components/switch.mqtt):

```yaml
switch:
- platform: mqtt
  command_topic: PREFIX/DEVICE/transmit
  body_on: CODE
  body_off: CODE
```

Where:

- `BRIDGE_HOST` is the hostname/IP address of this bridge
- `PORT` is the HTTP port (default `8780`)
- `PREFIX` is the MQTT prefix (default `broadlink`)
- `DEVICE` identifies the target [device](#device)
- `CODE` is the [code](#code) (or command) to transmit,
  prefixed by any [repeats](#repeats)

## Configuration

A configuration file can be optionally specified as a command-line argument. An [example file](config.example.ini) is provided.

### MQTT client

To enable the MQTT client, it is necessary to specify the URL of the MQTT
broker as the `broker_url` value inside the `[mqtt]` section.

The prefix for the MQTT topics is configurable via `topic_prefix`.

### Manually declared devices

Devices can be manually declared in the `[devices]` section. When a device is declared in this way it is given an *alias* which can act as an additional [identifier](#device) for the device in the bridge. Auto-discovered devices do not have aliases.

### Commands

Commands can be defined in the `[commands]` section. Commands associate a *name* with a *code*. The name can then be used anywhere where a code can appear.

The code for the command can be in [any supported format](#code) and contain
[repeats](#repeats), with the exception that it cannot be another command.

## Protocols

### Definitions

#### Device

A *device* represents a Broadlink device which can be addressed on any of the protocols.
It can be identified by any of the following:

- by its alias (as specified in the configuration file)
- by its host (as specified in the configuration file or found via discovery)
- by its MAC address
- by one of its IP addresses

When the device is not found via one of the mechanisms above, a final attempt
is made by interpreting *device* as a host: in case a device is discovered at
that address, then it is added to the list of known devices (this can be
considered a lazy discovery mechanism).

#### Default device

The *default device* is the [device](#device) with an alias of `default`. If there is no device with such an alias, it is the first declared or discovered device.

#### Code

The *code* is the data to transmit. It can have one of the following forms:

- IR/RF data in Broadlink format (encoded as base64):
  `JgAcAB0dHB44HhweGx4cHR06HB0cHhwdHB8bHhwADQUAAAAAAAAAAAAAAAA=`
- IR data in Pronto hex format:

  ```
  0000 006C 0022 0002 015B 00AD 0016 0016 0016 0016 0016 0041 0016 0016 0016
  0016 0016 0016 0016 0016 0016 0016 0016 0041 0016 0041 0016 0016 0016 0041
  0016 0041 0016 0041 0016 0041 0016 0041 0016 0016 0016 0016 0016 0041 0016
  0016 0016 0016 0016 0016 0016 0041 0016 0041 0016 0041 0016 0041 0016 0016
  0016 0041 0016 0041 0016 0041 0016 0016 0016 0016 0016 05F7 015B 0057 0016
  0E6C
  ```

- a *command* defined via the configuration file: in that case the code for
  the command is used (which can have any of the above forms)

Note that codes can contain repeats (see next section).

#### Repeats

*Repeats* are the number of times a *code* will be retransmitted.
Repeats can be specified in multiple ways:

- as part of the code — if the code starts with `N*` (number plus asterisk)
  then the code will be sent `N` times (`N-1` repeats), for example:
  - `3 * JgAcAB...` (Broadlink format, sent 3 times)
  - `2 * 0000 006C ...` (Pronto hex format, sent 2 times)
  - `5 * tv/on` (command defined via configuration file, sent 5 times)
- inside Broadlink data packet (second data byte is the number of repeats)
- via the protocol command (in case of LIRC)

When repeats are specified in more than one way, their effects multiply.
For example, LIRC command `SEND_ONCE default 3*tv/on 1` (1 being the repeat
and `tv/on` being a command defined in the configuration file as `2*JgAcAB...`)
will result in the code being sent 2x3x2 = 12 times (11 repeats).

### HTTP

verb | path | description
--|--|--
POST | /devices/*device*  | transmits the submitted [code](#code) via [device](#device)

Status codes:

- `404` when the device is unknown
- `400` when the code is invalid or not recognized

### MQTT

The topic *prefix* defaults to `broadlink` and can be changed via the configuration file.

topic | description
--|--
*prefix*/devices/*device*/transmit  | transmits the submitted [code](#code) via [device](#device)

### LIRC

A subset of the [LIRC command interface](http://www.lirc.org/html/lircd.html) and the unofficial [CCF extension](http://www.harctoolbox.org/lirc_ccf.html) is supported.

command | description
--|--
SEND_ONCE *device* *code* [*repeat*] | transmits the given [code](#code) (no spaces) via [device](#device), optionally repeating it *repeat* times
SEND_CCF_ONCE *repeat* *code* | transmits the given [code](#code) (spaces allowed) via the [default device](#default-device), repeating it *repeat* times
LIST | replies with all known devices
LIST *device* | replies with all defined commands (commands are not device-specific)
VERSION | replies with bridge version
