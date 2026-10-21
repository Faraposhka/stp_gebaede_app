"""Serve the app with byte-range support required by PMTiles."""
import os
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RangeRequestHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            return super().send_head()

        try:
            file = path.open("rb")
            stat = path.stat()
        except OSError:
            self.send_error(404, "File not found")
            return None

        size = stat.st_size
        etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
        if_match = self.headers.get("If-Match")
        if if_match and if_match != etag:
            file.close()
            self.send_error(412, "File changed since metadata request")
            return None

        start, end, status = 0, size - 1, 200
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
            if not match or (not match.group(1) and not match.group(2)) or size == 0:
                file.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return None

            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else size - 1
            else:
                suffix_length = int(match.group(2))
                start = max(0, size - suffix_length)
            if start >= size or end < start:
                file.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return None
            end = min(end, size - 1)
            status = 206

        self.send_response(status)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", etag)
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        file.seek(start)
        return file


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8080"))
    handler = partial(RangeRequestHandler, directory=str(ROOT))
    with ThreadingHTTPServer(("0.0.0.0", port), handler) as server:
        print(f"Serving {ROOT} on http://localhost:{port}")
        server.serve_forever()