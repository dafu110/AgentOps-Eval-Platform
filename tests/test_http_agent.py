import json
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        response = json.dumps({"data": {"answer": f"received {payload['input']}"}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return


class HttpAgentTests(unittest.TestCase):
    def test_http_agent_posts_stdin_and_prints_output_field(self):
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/invoke"
            completed = subprocess.run(
                ["python", "-m", "agentops_eval.http_agent", "--url", url, "--output-field", "data.answer"],
                input="hello",
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "received hello")


if __name__ == "__main__":
    unittest.main()
