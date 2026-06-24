# Smart Bird WiFi Plug Control

Codex skill and TCP control script for Smart Bird / GemeOpen GSPM1B WiFi smart plugs.

This repository contains a Codex skill plus a small Python TCP tool for controlling and debugging a Smart Bird / GemeOpen WiFi socket on a local network.

## What It Supports

- Run a TCP server for the plug to connect to
- Query device status with `{"type":"info"}`
- Turn the socket on and off
- Send raw JSON commands from the official GemeOpen command documentation
- Record protocol notes for future Codex sessions

## Files

```text
SKILL.md                       Codex skill instructions
agents/openai.yaml             Skill UI metadata
references/protocol.md         Protocol and command notes
scripts/smart_bird_plug.py     TCP server/client control script
```

## TCP Control Model

The official GemeOpen TCP debugging flow expects the computer to run a TCP server. The plug connects out to that server after custom TCP settings are configured and the device is restarted or power-cycled.

That means the plug may be pingable while refusing inbound TCP connections on its own IP address. This is expected.

For the tested setup:

```text
plug IP:      learn from `client connected: <ip>:<port>` in server mode
server IP:    192.168.0.103
server port:  4444
```

Configure the plug custom TCP settings with the server IP and port, then restart or power-cycle the plug.

## Usage

Start the TCP server:

```bash
python3 scripts/smart_bird_plug.py server --host 0.0.0.0 --port 4444
```

When the plug connects, use interactive commands:

```text
info
on
off
send {"type":"setting","timerEnable":1,"timerInterval":20}
quit
```

If you have firmware or a proxy that listens for inbound TCP, client mode is also available:

```bash
python3 scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 info
python3 scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 on
python3 scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 off
```

## Common Commands

Query info:

```json
{"type":"info"}
```

Turn on:

```json
{"type":"event","key":1,"messageId":"generated-id"}
```

Turn off:

```json
{"type":"event","key":0,"messageId":"generated-id"}
```

Restart:

```json
{"type":"setting","system":"restart","messageId":"generated-id"}
```

Factory reset, only when explicitly intended:

```json
{"type":"setting","system":"reset","messageId":"generated-id"}
```

## Verified Device

Tested with:

```text
model:   GSPM1B
ip:      learn from server-mode client address
mac:     8cce4e513fbb
version: 2.3.3
```

The plug successfully connected to the local TCP server, returned `info`, accepted `on`, and accepted `off`. Final tested state was `key: 0`.

## Notes

- The script uses only the Python standard library.
- JSON is sent as UTF-8 followed by a newline.
- See `references/protocol.md` for more protocol details and source links.
