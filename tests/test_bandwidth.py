"""Tests for active bandwidth measurement against a local HTTP server."""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from python_zte_mc801a.lib.bandwidth import measure_bandwidth

_CHUNK = b"\0" * 65536


class _FastHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        for _ in range(1000):  # up to ~64 MB
            try:
                self.wfile.write(_CHUNK)
            except (BrokenPipeError, ConnectionResetError):
                return

    def log_message(self, *args):
        pass


class _SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        for _ in range(1000):
            try:
                self.wfile.write(_CHUNK)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(0.05)  # throttle to ~1.3 MB/s

    def log_message(self, *args):
        pass


class _EmptyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


def _serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_measure_caps_on_bytes():
    srv = _serve(_FastHandler)
    port = srv.server_address[1]
    try:
        r = measure_bandwidth(f"http://127.0.0.1:{port}/", max_bytes=1_000_000, max_seconds=10)
    finally:
        srv.shutdown()
    assert r["bytes"] >= 1_000_000
    assert r["capped_by"] == "bytes"
    assert r["mbps"] > 0
    assert r["seconds"] >= 0  # a sub-millisecond loopback transfer rounds to 0.000s


def test_measure_caps_on_time():
    srv = _serve(_SlowHandler)
    port = srv.server_address[1]
    try:
        r = measure_bandwidth(f"http://127.0.0.1:{port}/", max_bytes=100_000_000, max_seconds=0.5)
    finally:
        srv.shutdown()
    assert r["capped_by"] == "seconds"
    assert r["bytes"] < 100_000_000
    assert r["seconds"] <= 3.0  # generous slack for a loaded box


def test_measure_empty_body_returns_zero():
    srv = _serve(_EmptyHandler)
    port = srv.server_address[1]
    try:
        r = measure_bandwidth(f"http://127.0.0.1:{port}/", max_bytes=1_000_000, max_seconds=5)
    finally:
        srv.shutdown()
    assert r["bytes"] == 0
    assert r["mbps"] == 0.0
    assert r["capped_by"] == "empty"
