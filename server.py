from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import tempfile

PORT = int(os.environ.get("PORT", 5000))

class SVHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/run":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        code = self.rfile.read(length).decode("utf-8")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                sv_file = os.path.join(tmpdir, "design.sv")
                out_file = os.path.join(tmpdir, "sim")

                with open(sv_file, "w") as f:
                    f.write(code)

                # Compile
                compile_result = subprocess.run(
                    ["iverilog", "-g2012", "-o", out_file, sv_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if compile_result.returncode != 0:
                    self._respond(200, "COMPILE ERROR:\n" + compile_result.stderr)
                    return

                # Simulate
                sim_result = subprocess.run(
                    ["vvp", out_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                output = sim_result.stdout + sim_result.stderr
                self._respond(200, output if output else "No output")

        except FileNotFoundError:
            self._respond(200, "ERROR: iverilog not found!")
        except Exception as e:
            self._respond(200, "ERROR: " + str(e))

    def do_GET(self):
        self._respond(200, "SV Server OK")

    def _respond(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), SVHandler)
    server.serve_forever()
