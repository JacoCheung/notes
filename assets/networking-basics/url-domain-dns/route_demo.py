#!/usr/bin/env python3
"""Two URL routes, one handler. Run locally with Python 3.8 or newer."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def development_page():
    return b"<!doctype html><title>Development</title><h1>Shared development page</h1>\n"


ROUTES = {
    ("dev.example.com", "/"): development_page,
    ("example.com", "/dev"): development_page,
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.respond(send_body=True)

    def do_HEAD(self):
        self.respond(send_body=False)

    def respond(self, send_body):
        try:
            host = urlsplit("//" + self.headers.get("Host", "")).hostname
            path = urlsplit(self.path).path
        except ValueError:
            self.send_error(400, "Invalid request target or Host")
            return

        if (host, path) == ("example.com", "/redirect-dev"):
            self.send_response(302)
            self.send_header("Location", "http://dev.example.com:%d/" % self.server.server_port)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        handler = ROUTES.get((host, path))
        if handler is None:
            self.send_error(404)
            return

        body = handler()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print("Listening on 127.0.0.1:%d; Ctrl-C to stop" % server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
