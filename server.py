"""
SystemVerilog Simulation Server for Railway
-------------------------------------------
Uses ONLY Python stdlib (no external dependencies!)

Works on Railway Docker deployment.
Receives SV code from your Pico 2W cyberdeck,
runs it with iverilog, and returns the output.

Railway auto-installs iverilog via Dockerfile.
Just deploy this code!
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import tempfile
import sys

PORT = int(os.environ.get("PORT", 5000))

class SVHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        """Handle POST requests with SV code"""
        if self.path != "/run":
            self.send_error(404, "Only /run is supported")
            return

        # Read incoming SV code
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._respond(400, "No code received")
            return

        try:
            code = self.rfile.read(length).decode("utf-8")
        except Exception as e:
            self._respond(400, f"Error reading code: {str(e)}")
            return

        print("\n" + "="*50)
        print("RECEIVED CODE:")
        print("="*50)
        print(code)
        print("="*50)

        # Create temp directory for compilation
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                sv_file  = os.path.join(tmpdir, "design.sv")
                out_file = os.path.join(tmpdir, "sim")

                # Write SV code to file
                with open(sv_file, "w") as f:
                    f.write(code)

                # STEP 1: Compile with iverilog
                print("\nCompiling...")
                compile_result = subprocess.run(
                    ["iverilog", "-g2012", "-o", out_file, sv_file],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                if compile_result.returncode != 0:
                    # Compilation failed
                    error_msg = "❌ COMPILE ERROR:\n" + compile_result.stderr
                    print(error_msg)
                    self._respond(200, error_msg)
                    return

                print("✅ Compilation successful")

                # STEP 2: Simulate with vvp
                print("Simulating...")
                sim_result = subprocess.run(
                    ["vvp", out_file],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                # Collect output
                output = ""
                if sim_result.stdout:
                    output += sim_result.stdout
                if sim_result.stderr:
                    output += "\n⚠️  WARNINGS:\n" + sim_result.stderr

                if not output.strip():
                    output = "✅ Simulation complete (no output — add $display() to see results)"

                print("\nOUTPUT:")
                print(output)
                print("="*50)

                self._respond(200, output)

        except subprocess.TimeoutExpired:
            self._respond(200, "❌ Timeout: Simulation took too long (>15s)")
        except Exception as e:
            self._respond(200, f"❌ Error: {str(e)}")

    def do_GET(self):
        """Health check"""
        html = """
        <html><body style="font-family:monospace; padding:20px;">
        <h2>🔧 SystemVerilog Simulation Server</h2>
        <p>Server is running!</p>
        <p><b>Usage:</b></p>
        <pre>POST /run
Content-Type: text/plain

&lt;your systemverilog code here&gt;
        </pre>
        <p>Returns simulation output or compile errors.</p>
        </body></html>
        """
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, code, text):
        """Send response back to client"""
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass


if __name__ == "__main__":
    print("\n" + "╔" + "="*48 + "╗")
    print(f"║  🔬 SystemVerilog Server on port {PORT:<32} ║")
    print("║  POST /run for simulation                        ║")
    print("║  GET  /    for status                            ║")
    print("║  Ctrl+C to stop                                  ║")
    print("╚" + "="*48 + "╝\n")

    # Check if iverilog is available
    try:
        result = subprocess.run(
            ["iverilog", "-v"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ iverilog is installed\n")
        else:
            print("⚠️  iverilog check failed (but continuing...)\n")
    except FileNotFoundError:
        print("⚠️  iverilog not found in PATH!")
        print("   Install with: sudo apt install iverilog\n")
    except Exception as e:
        print(f"⚠️  Could not verify iverilog: {e}\n")

    # Start server
    server = HTTPServer(("0.0.0.0", PORT), SVHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped.")
        sys.exit(0)
