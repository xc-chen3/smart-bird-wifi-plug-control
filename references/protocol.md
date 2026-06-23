# Smart Bird / GemeOpen GSPM1B TCP Protocol Notes

Sources checked 2026-06-23:

- Debug guide: `https://www.smart-bird.cn/doc/column/173/child/214`
- GSPM1B commands: `https://www.smart-bird.cn/doc/product/GSPM/device/GSPM1B/command`
- Backing APIs observed from the docs frontend:
  - `https://api.smart-bird.cn/node-help-v3/page/getColumnWebContent/214`
  - `https://api.smart-bird.cn/document/open/getProductCommandOverViewList/GSPM1B`

## TCP Debugging Flow

The official TCP guide describes this flow:

1. Run NetAssist or another TCP Server on the computer.
2. Put the device in configuration mode.
3. Connect to the device hotspot and open `192.168.4.1`.
4. In custom TCP settings, enter the computer's host IP and server port.
5. Save, then restart or power-cycle the device so the custom TCP settings take effect.
6. The device connects to the TCP Server.
7. Send JSON commands over that established socket.

This means local TCP control is normally server-side from the computer perspective. The device IP, for example `192.168.0.108`, can be pingable while not accepting inbound TCP.

## Command Payloads

Send UTF-8 JSON. The bundled script sends compact JSON followed by `\n`.

### Query Info

```json
{"type":"info"}
```

### Control Outlet

Command name: `controller-event`.

Turn on:

```json
{"type":"event","key":1,"messageId":"generated-id"}
```

Turn off:

```json
{"type":"event","key":0,"messageId":"generated-id"}
```

`key` is the outlet relay state: `0` means off/disconnected, `1` means on/energized.

Expected response includes fields such as:

```json
{
  "messageId": "generated-id",
  "commandName": "controller-event",
  "source": "command",
  "mac": "4CEBD60BFD62",
  "type": "Socket-mini",
  "version": "2.0.0",
  "key": 1,
  "wifiLock": 0,
  "keyLock": 0,
  "signal": -47,
  "timerEnable": 0,
  "onState": 1,
  "ip": "192.168.122.119",
  "ssid": "GeekOpen"
}
```

### Restart

```json
{"type":"setting","system":"restart","messageId":"generated-id"}
```

### Factory Reset

Only send when explicitly requested:

```json
{"type":"setting","system":"reset","messageId":"generated-id"}
```

### Timer Reporting

Enable periodic reporting:

```json
{"type":"setting","timerEnable":1,"timerInterval":20,"messageId":"generated-id"}
```

`timerInterval` is in seconds. Official docs list ranges such as `5-86400` for related reporting intervals.

### Configure Custom TCP

The command page also documents custom TCP configuration through the upstream MQTT/API command path:

```json
{
  "type": "custom",
  "protocol": "tcp",
  "server": "192.168.0.66",
  "port": "4444",
  "messageId": "generated-id"
}
```

After custom TCP settings, restart or power-cycle the device.
