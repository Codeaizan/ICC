from __future__ import annotations

import argparse
import json
import logging
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, output_dir=None, **kwargs):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        # The static files are located relative to this python file
        self.static_dir = Path(__file__).parent / "static"
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path).path

        if parsed_path == "/api/cases":
            self.send_cases()
        elif parsed_path.startswith("/api/case/"):
            case_id = parsed_path.split("/")[-1]
            self.send_case_details(case_id)
        elif parsed_path.startswith("/data/"):
            # Serve files from the output directory (e.g. overlay.png)
            rel_path = parsed_path[len("/data/"):]
            file_path = self.output_dir / rel_path
            self.serve_file(file_path)
        elif parsed_path.startswith("/static/"):
            # Serve css/js
            rel_path = parsed_path[len("/static/"):]
            file_path = self.static_dir / rel_path
            self.serve_file(file_path)
        elif parsed_path == "/":
            self.serve_file(self.static_dir / "index.html")
        else:
            self.send_error(404, "Not Found")

    def send_cases(self):
        cases = []
        if self.output_dir.exists():
            for case_dir in sorted(self.output_dir.iterdir()):
                if case_dir.is_dir() and (case_dir / "result.json").exists():
                    try:
                        report = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
                        cases.append({"case_id": case_dir.name, "status": report.get("status", "unknown")})
                    except (OSError, json.JSONDecodeError):
                        continue
        self.send_json(cases)

    def send_case_details(self, case_id: str):
        result_path = self.output_dir / case_id / "result.json"
        if not result_path.exists():
            self.send_error(404, "Case not found")
            return
        
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.send_json(data)
        except (OSError, json.JSONDecodeError) as e:
            self.send_error(500, f"Error reading case: {e!s}")

    def serve_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404, "File not found")
            return
        
        try:
            with path.open("rb") as f:
                content = f.read()
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type:
                self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass # Client aborted the request (e.g. React Strict Mode)
        except OSError:
            self.send_error(404, "File not found")

    def send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    # Suppress default logging to stdout
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="Start the ASPECTS Clinician-Facing Viewer")
    parser.add_argument("--output", required=True, help="Path to the outputs directory containing case folders")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    if not output_dir.exists():
        print(f"Error: Output directory {output_dir} does not exist.")
        return

    def handler_factory(*args, **kwargs):
        return ViewerHandler(*args, output_dir=output_dir, **kwargs)

    server_address = ('', args.port)
    httpd = ThreadingHTTPServer(server_address, handler_factory)
    
    print(f"Starting viewer at http://localhost:{args.port}")
    print(f"Serving outputs from: {output_dir}")
    print("Press Ctrl+C to stop.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == "__main__":
    main()
