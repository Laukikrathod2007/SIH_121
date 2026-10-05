"""
Direct TCP client for the blender-mcp addon (ahujasid/blender-mcp), which
listens on localhost:9876 inside a running Blender instance. No formal MCP
tool for this server is registered in this Claude session, so this connects
directly using the same plain-JSON-over-TCP protocol the real MCP tool
wrapper uses: send {"type": "<command>", "params": {...}}, receive
{"status": "success"/"error", "result"/"message": ...}.

Usage: python blender_client.py <command_type> '<json_params>'
   or: from blender_client import send_command; send_command("execute_blender_code", {"code": "..."})
"""
import json
import socket
import sys

HOST = "localhost"
PORT = 9876


_decoder = json.JSONDecoder()


def send_command(cmd_type: str, params: dict | None = None, timeout: float = 60.0) -> dict:
    payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
        sock.sendall(payload)
        sock.settimeout(timeout)
        chunks = []
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            # The server sends no length prefix and (found empirically) can
            # emit more than one JSON value back-to-back on the same
            # connection -- raw_decode parses just the FIRST complete value
            # from the start of the buffer and tells us where it ended,
            # instead of json.loads's all-or-nothing parse which fails with
            # "Extra data" the moment anything trails the first object.
            text = b"".join(chunks).decode("utf-8", errors="ignore").lstrip()
            if not text:
                continue
            try:
                obj, _end = _decoder.raw_decode(text)
                return obj
            except json.JSONDecodeError:
                continue
        raise ConnectionError("No parseable response received from Blender MCP on port 9876 -- is Blender running with the addon enabled?")


def run_python(code: str, timeout: float = 300.0) -> dict:
    """Convenience wrapper for the execute_blender_code command."""
    return send_command("execute_blender_code", {"code": code}, timeout=timeout)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python blender_client.py <command_type> ['<json_params>']")
        sys.exit(1)
    cmd = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result = send_command(cmd, params)
    print(json.dumps(result, indent=2))
