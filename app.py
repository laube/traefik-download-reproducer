import os
import re
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler


ALL_CONFIGURATIONS = [
    ("none", "Direct access", "http://localhost:16180/"),
    ("traefik", "Traefik", "https://localhost:16243/"),
    ("nginx", "Nginx", "https://localhost:16343/"),
    ("traefik-nginx", "Traefik-Nginx", "https://localhost:16443/"),
    ("nginx-nginx", "Nginx-Nginx", "https://localhost:16543/"),
    ("nginx-traefik", "Nginx-Traefik", "https://localhost:16643/"),
]


class SlowRequestWhichCrashes(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path == "/":
            self.generate_html_page()
        elif m := re.match(r"/content/(?P<repetitions>\d+)/(?P<how_to_die>kill|exc|close)", self.path):
            self.generate_crash_download(repetitions=int(m.group("repetitions")), how_to_die=m.group("how_to_die"))
        else:
            self.send_response_only(HTTPStatus.NOT_FOUND)

    def generate_html_page(self):
        proxy_config_from_header = self.get_proxy_names()

        other_servers_li = "\n".join(
            f'<li><a href="{url}">{name}</a></li>' if proxy_config != proxy_config_from_header else f"<li>{name}</li>"
            for proxy_config, name, url in ALL_CONFIGURATIONS
        )

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Amazing Website [{proxy_config_from_header}]</title>
        </head>
        <body>
            <h3>Reverse Proxy: {proxy_config_from_header}</h3>
            <h5>Protocol:</h5>
            <p id="protocol">
            </p>
            <h5>Test Downloads:</h5>
            <p>
                Each of these downloads fails the request after generating half of the response.
                Exactly how it fails depends on which URL you download.
            </p>
            <ul>
                <li>
                    <a href="/content/5000/kill">Download 5000 repetitions but kill the app</a>
                </li>
                <li>
                    <a href="/content/50000/kill">Download 50000 repetitions but kill the app</a>
                </li>
                <li>
                    <a href="/content/5000/close">Download 5000 repetitions but close the connection</a>
                </li>
                <li>
                    <a href="/content/50000/close">Download 50000 repetitions but close the connection</a>
                </li>
                <li>
                    <a href="/content/5000/exc">Download 5000 repetitions but throw an exception</a>
                </li>
                <li>
                    <a href="/content/50000/exc">Download 50000 repetitions but throw an exception</a>
                </li>
            </ul>
            <p>The download should fail. If it doesn't there is a bug somewhere.</p>
            <p>
                You should also definitely not see <code>"If you can read this, it is complete."</code> at the
                end of the file.
            </p>
            <h5>Visit the other configurations:</h5>
            <ul>
                {other_servers_li}
            </ul>
        </body>
        <script>
            window.addEventListener("load", () => {{
              document.getElementById("protocol").innerText =
               `${{location.protocol}} / ${{performance.getEntries()[0].nextHopProtocol}}`
            }})
        </script>
        </html>
        """.encode()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def generate_crash_download(self, repetitions: int, how_to_die: str):
        proxy_config = self.get_proxy_names()

        block_size = 100000

        full_text = (
            f"PATH: {self.path}\nTotal size is {repetitions} repetitions but it crashes our process midway "
            f"while writing in blocks of {block_size}\n".encode()
            + open(__file__, "rb").read() * repetitions
            + b"\nIf you can read this, it is complete.\n"
        )

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Disposition", f"attachment; filename=Some File via {proxy_config}.txt")
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(full_text)))
        self.end_headers()

        for chunk_idx in range(0, len(full_text), block_size):
            self.wfile.write(full_text[chunk_idx : chunk_idx + block_size])
            if chunk_idx == 0:
                # Flush the first chunk to force the response to be started
                self.wfile.flush()

            if chunk_idx > len(full_text) / 2:
                if how_to_die == "kill":
                    print("Bye bye!", flush=True)
                    os._exit(1)
                elif how_to_die == "close":
                    print("Closing the file 😈", flush=True)
                    self.wfile.close()
                    return
                elif how_to_die == "exc":
                    raise ValueError("woops I can't seem to generate the content :-(")
                else:
                    raise AssertionError(f"Don't know how to '{how_to_die}'")

    def get_proxy_names(self):
        proxy_names = self.headers.get("X-L2-Proxy-Name", ""), self.headers.get("X-Proxy-Name", "none")
        return "-".join(n for n in proxy_names if n)


if __name__ == "__main__":
    with ThreadingHTTPServer(("0.0.0.0", 3000), SlowRequestWhichCrashes) as server:
        for _, name, url in ALL_CONFIGURATIONS:
            print(f"{name:13}: {url}")
        server.serve_forever()
