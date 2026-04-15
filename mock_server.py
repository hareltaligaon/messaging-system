"""
mock_server.py - Local mock for the external sending service
Simulates the external sending API for local development.
Always returns HTTP 200 OK.

Usage:
    python mock_server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

PORT = 9999


class MockHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
            logger.info(f"Received message: id={data.get('message_id')} destination={data.get('destination')}")
        except Exception:
            logger.info("Received request (could not parse body)")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, *args):
        pass  # Suppress default HTTP logs (we use our own)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), MockHandler)
    logger.info(f"Mock sending service running on http://localhost:{PORT}/send")
    server.serve_forever()
