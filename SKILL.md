---
name: wifi-plug-control
description: Control and debug Smart Bird / GemeOpen WiFi smart plugs such as GSPM1B over LAN TCP. Use when Codex needs to query status, turn the plug on or off, send JSON device commands, run a TCP server for the plug to connect to, or troubleshoot local-network TCP control for a Smart Bird WiFi socket.
---

# WiFi Plug Control

## Quick Start

Use `scripts/smart_bird_plug.py`. Do not assume a fixed plug IP. Prefer server mode and identify the current plug IP from the client address printed when the plug connects.

For normal TCP debugging, run a TCP server on the machine Codex is using, then configure the plug's custom TCP settings to connect to that host and port:

```bash
python3 wifi-plug-control/scripts/smart_bird_plug.py server --host 0.0.0.0 --port 4444
```

When the device connects, use interactive commands:

```text
info
on
off
send {"type":"setting","timerEnable":1,"timerInterval":20}
quit
```

For one-shot control, wait for the plug to connect and then send a command automatically:

```bash
python3 wifi-plug-control/scripts/smart_bird_plug.py wait-on --host 0.0.0.0 --port 4444
python3 wifi-plug-control/scripts/smart_bird_plug.py wait-off --host 0.0.0.0 --port 4444
```

The script prints `client connected: <ip>:<port>`; treat that `<ip>` as the plug's current LAN IP.

If the user has a TCP proxy or firmware that listens on the device IP, use client mode:

```bash
python3 wifi-plug-control/scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 info
python3 wifi-plug-control/scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 on
python3 wifi-plug-control/scripts/smart_bird_plug.py client --host <plug-ip-from-server-mode> --port 4444 off
```

## Important TCP Model

The official TCP debugging flow expects the computer to run a **TCP Server**. The plug connects out to that server after custom TCP settings are saved and the plug is power-cycled or restarted.

Do not assume the plug listens for inbound LAN TCP connections. If `nc -vz <device-ip> <port>` returns connection refused but ping works, this is consistent with the documented flow.

Read `references/protocol.md` before changing command payloads or troubleshooting protocol behavior.

## Common Commands

- Query device information: `{"type":"info"}`
- Turn outlet on: `{"type":"event","key":1,"messageId":"..."}`
- Turn outlet off: `{"type":"event","key":0,"messageId":"..."}`
- Restart device: `{"type":"setting","system":"restart","messageId":"..."}`
- Factory reset: `{"type":"setting","system":"reset","messageId":"..."}`

Avoid sending reset unless the user explicitly asks for factory reset.

## Troubleshooting

If no client connects to server mode:

1. Confirm the plug is on the same WiFi/LAN as the computer.
2. Confirm the plug custom TCP settings point to the computer's LAN IP, not `127.0.0.1`.
3. Confirm the chosen port is open through the OS firewall.
4. Power-cycle the plug after saving custom TCP settings.
5. Use ping only as a reachability check after learning the current IP from server mode; ping success does not mean the plug is listening for TCP.

If commands receive no response:

1. Try newline-delimited JSON first; the bundled script already appends `\n`.
2. Use `send` in server mode to send the exact JSON from the official command page.
3. Check whether the device has connected but is not the active client selected by the script.
