#!/usr/bin/env python3
"""Simple reverse proxy for xdaily deployment."""
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import re

FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 3000  # API requests go to Next.js which proxies to backend
PORT = 80

class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.proxy_request(BACKEND_HOST, BACKEND_PORT)
        else:
            self.proxy_request(FRONTEND_HOST, FRONTEND_PORT)

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.proxy_request(BACKEND_HOST, BACKEND_PORT)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        if self.path.startswith('/api/'):
            self.proxy_request(BACKEND_HOST, BACKEND_PORT)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self.proxy_request(BACKEND_HOST, BACKEND_PORT)
        else:
            self.send_error(405, "Method Not Allowed")

    def proxy_request(self, host, port):
        try:
            # Parse path and query string
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            query = parsed.query

            # Build the URL
            url = f"http://{host}:{port}{path}"
            if query:
                url += f"?{query}"

            # Prepare headers
            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in ('host', 'connection'):
                    headers[key] = value
            headers['Connection'] = 'close'
            headers['X-Forwarded-For'] = self.client_address[0]
            headers['X-Forwarded-Host'] = self.headers.get('Host', '')

            # Read body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # Make the request
            req = urllib.request.Request(url, method=self.command, data=body, headers=headers)
            response = urllib.request.urlopen(req, timeout=30)

            # Send response back to client
            self.send_response(response.status)
            for key, value in response.headers.items():
                if key.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(key, value)
            self.send_header('Connection', 'close')
            self.end_headers()

            # Write response body
            self.wfile.write(response.read())

        except urllib.error.HTTPError as e:
            # Pass through HTTP errors (401, 403, 404, etc.)
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(key, value)
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(e.read())

        except Exception as e:
            self.send_error(502, f"Proxy Error: {str(e)}")

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"Reverse proxy running on port {PORT}")
        print(f"  /      -> http://{FRONTEND_HOST}:{FRONTEND_PORT}")
        print(f"  /api/* -> http://{BACKEND_HOST}:{BACKEND_PORT}")
        httpd.serve_forever()
