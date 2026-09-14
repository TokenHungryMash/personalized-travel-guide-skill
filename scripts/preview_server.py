"""Serve one workbench on an OS-assigned loopback port; print its identity."""
import argparse
import functools
import hashlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench', type=Path)
    args = parser.parse_args()
    root = args.workbench.resolve()
    index = root / 'index.html'
    if not index.is_file():
        parser.error('workbench must contain index.html')
    identity = {'root': str(root), 'index_sha256': hashlib.sha256(index.read_bytes()).hexdigest()}

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/__travel_preview_identity__':
                data = json.dumps(identity).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                super().do_GET()

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

    with ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(root))) as server:
        identity['url'] = f'http://127.0.0.1:{server.server_port}/index.html'
        print(json.dumps(identity), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
