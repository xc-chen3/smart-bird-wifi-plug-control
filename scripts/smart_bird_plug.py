#!/usr/bin/env python3
"""Control Smart Bird / GemeOpen WiFi plugs over a LAN TCP socket."""

from __future__ import annotations

import argparse
import json
import queue
import selectors
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_DEVICE_HOST = "192.168.0.108"
DEFAULT_PORT = 4444


def message_id() -> str:
    return time.strftime("%Y%m%d%H%M%S") + f"{int((time.time() % 1) * 1000):03d}"


def payload_for(command: str, raw_json: str | None = None) -> dict[str, Any]:
    if command == "info":
        return {"type": "info"}
    if command == "on":
        return {"type": "event", "key": 1, "messageId": message_id()}
    if command == "off":
        return {"type": "event", "key": 0, "messageId": message_id()}
    if command == "restart":
        return {"type": "setting", "system": "restart", "messageId": message_id()}
    if command == "reset":
        return {"type": "setting", "system": "reset", "messageId": message_id()}
    if command == "raw":
        if not raw_json:
            raise ValueError("raw command requires JSON")
        value = json.loads(raw_json)
        if not isinstance(value, dict):
            raise ValueError("raw JSON must be an object")
        return value
    raise ValueError(f"unsupported command: {command}")


def encode_payload(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def format_rx(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        return repr(data)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)


def run_client(args: argparse.Namespace) -> int:
    payload = payload_for(args.command, args.json)
    data = encode_payload(payload)
    print(f"connecting to {args.host}:{args.port} ...", flush=True)
    with socket.create_connection((args.host, args.port), timeout=args.timeout) as sock:
        sock.settimeout(args.timeout)
        print(f"tx: {data.decode('utf-8').strip()}", flush=True)
        sock.sendall(data)
        chunks: list[bytes] = []
        deadline = time.monotonic() + args.read_window
        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk or b"}" in chunk:
                break
        if chunks:
            print("rx:")
            print(format_rx(b"".join(chunks)))
        else:
            print("rx: <no response before timeout>")
    return 0


@dataclass
class Client:
    sock: socket.socket
    addr: tuple[str, int]


class TcpServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.clients: dict[int, Client] = {}
        self.commands: "queue.Queue[str]" = queue.Queue()
        self.running = True

    def start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen()
        listener.setblocking(False)
        self.selector.register(listener, selectors.EVENT_READ, self._accept)
        print(f"tcp server listening on {self.host}:{self.port}", flush=True)
        print("waiting for plug connection. type 'help' for commands.", flush=True)

        input_thread = threading.Thread(target=self._read_stdin, daemon=True)
        input_thread.start()

        try:
            while self.running:
                for key, _ in self.selector.select(timeout=0.2):
                    callback = key.data
                    callback(key.fileobj)
                self._drain_commands()
        finally:
            self.selector.close()

    def _accept(self, listener: socket.socket) -> None:
        sock, addr = listener.accept()
        sock.setblocking(False)
        self.clients[sock.fileno()] = Client(sock=sock, addr=addr)
        self.selector.register(sock, selectors.EVENT_READ, self._read_client)
        print(f"client connected: {addr[0]}:{addr[1]}", flush=True)

    def _read_client(self, sock: socket.socket) -> None:
        client = self.clients.get(sock.fileno())
        try:
            data = sock.recv(8192)
        except ConnectionError:
            data = b""
        if not data:
            self._close_client(sock)
            return
        prefix = f"rx from {client.addr[0]}:{client.addr[1]}" if client else "rx"
        print(prefix + ":")
        print(format_rx(data), flush=True)

    def _close_client(self, sock: socket.socket) -> None:
        client = self.clients.pop(sock.fileno(), None)
        try:
            self.selector.unregister(sock)
        except Exception:
            pass
        sock.close()
        if client:
            print(f"client disconnected: {client.addr[0]}:{client.addr[1]}", flush=True)

    def _read_stdin(self) -> None:
        while self.running:
            line = sys.stdin.readline()
            if not line:
                self.commands.put("quit")
                return
            self.commands.put(line.strip())

    def _drain_commands(self) -> None:
        while True:
            try:
                line = self.commands.get_nowait()
            except queue.Empty:
                return
            self._handle_command(line)

    def _active_client(self) -> Client | None:
        if not self.clients:
            return None
        return next(reversed(self.clients.values()))

    def _handle_command(self, line: str) -> None:
        if not line:
            return
        if line in {"quit", "exit"}:
            self.running = False
            return
        if line == "help":
            print("commands: clients, info, on, off, restart, send <json>, quit", flush=True)
            return
        if line == "clients":
            if not self.clients:
                print("no clients connected", flush=True)
                return
            for client in self.clients.values():
                print(f"{client.addr[0]}:{client.addr[1]}", flush=True)
            return

        try:
            if line.startswith("send "):
                payload = payload_for("raw", line[5:].strip())
            else:
                payload = payload_for(line)
        except Exception as exc:
            print(f"invalid command: {exc}", flush=True)
            return

        client = self._active_client()
        if not client:
            print("no connected plug client yet", flush=True)
            return
        data = encode_payload(payload)
        try:
            client.sock.sendall(data)
        except ConnectionError as exc:
            print(f"send failed: {exc}", flush=True)
            self._close_client(client.sock)
            return
        print(f"tx to {client.addr[0]}:{client.addr[1]}: {data.decode('utf-8').strip()}", flush=True)


def run_server(args: argparse.Namespace) -> int:
    TcpServer(args.host, args.port).start()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    server = sub.add_parser("server", help="Run a TCP server for the plug to connect to")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=DEFAULT_PORT)
    server.set_defaults(func=run_server)

    client = sub.add_parser("client", help="Connect to a listening TCP endpoint and send one command")
    client.add_argument("command", choices=["info", "on", "off", "restart", "reset", "raw"])
    client.add_argument("--host", default=DEFAULT_DEVICE_HOST)
    client.add_argument("--port", type=int, default=DEFAULT_PORT)
    client.add_argument("--json", help="JSON object for the raw command")
    client.add_argument("--timeout", type=float, default=3.0)
    client.add_argument("--read-window", type=float, default=3.0)
    client.set_defaults(func=run_client)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
