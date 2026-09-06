#!/usr/bin/env python3
"""Local Cloudflare AI proxy that rotates accounts on 429."""
import http.server, http.client, json, os, random, re, socket, sys, time, urllib.request

DEFAULT_CREDENTIALS_URL = 'https://bitbucket.org/hermes-new/hermes/raw/main/credentials/cloudflare.txt'
CREDENTIALS_URL = os.environ.get('CF_CREDENTIALS_URL', DEFAULT_CREDENTIALS_URL)
LISTEN_HOST = os.environ.get('CF_PROXY_HOST', '127.0.0.1')
LISTEN_PORT = int(os.environ.get('CF_PROXY_PORT', '8788'))
MAX_RETRIES = int(os.environ.get('CF_MAX_RETRIES', '20'))


def load_accounts():
    """Fetch and parse blank-line-separated credential blocks."""
    with urllib.request.urlopen(CREDENTIALS_URL, timeout=30) as response:
        text = response.read().decode('utf-8')
    blocks = re.split(r'\n\s*\n', text.strip())
    accounts = []
    for block in blocks:
        acc = {}
        for line in block.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                acc[k.strip()] = v.strip()
        if acc.get('ACCOUNT_ID') and acc.get('API_KEY'):
            accounts.append(acc)
    return accounts


ACCOUNTS = load_accounts()
if not ACCOUNTS:
    raise RuntimeError(f'No Cloudflare credentials found at {CREDENTIALS_URL}')
print(f'Loaded {len(ACCOUNTS)} accounts from {CREDENTIALS_URL}', file=sys.stderr)


CURRENT_ACC = None
LAST_ACC_TS = 0
ACC_TTL = 15  # seconds


def pick_account(force=False):
    global CURRENT_ACC, LAST_ACC_TS
    now = time.time()
    if force or CURRENT_ACC is None or now - LAST_ACC_TS >= ACC_TTL:
        CURRENT_ACC = random.choice(ACCOUNTS)
        LAST_ACC_TS = now
    return CURRENT_ACC


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'{self.client_address[0]} - {fmt % args}', file=sys.stderr)

    def _send(self, status, body, headers=None):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if isinstance(body, str):
            data = body.encode('utf-8')
            self.send_header('Content-Length', len(data))
        else:
            data = body
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # Minimal health check
        if self.path == '/health':
            self._send(200, json.dumps({'ok': True, 'accounts': len(ACCOUNTS)}))
            return
        self._send(404, b'')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len else b''

        # Capture client headers we need to forward
        upstream_headers = {}
        for h in ['Content-Type', 'Accept']:
            if h in self.headers:
                upstream_headers[h] = self.headers[h]

        tried = set()
        last_status = 429
        last_body = b''

        while len(tried) < min(len(ACCOUNTS), MAX_RETRIES):
            acc = pick_account(force=len(tried) > 0)
            key = acc['API_KEY']
            if key in tried:
                continue
            tried.add(key)

            account_id = acc['ACCOUNT_ID']
            # Hermes may send /v1/chat/completions or /chat/completions depending on base_url
            up_path = self.path.removeprefix('/v1')
            path = f'/client/v4/accounts/{account_id}/ai/v1{up_path}'
            headers = {**upstream_headers, 'Authorization': f'Bearer {key}'}

            conn = http.client.HTTPSConnection('api.cloudflare.com', timeout=60)
            try:
                conn.request('POST', path, body=body, headers=headers)
                resp = conn.getresponse()
                resp_body = resp.read()
                status = resp.status

                # Successful or non-rate-limit client error: send it through
                if status != 429:
                    print(f'OK {account_id[:8]}... {status} {len(resp_body)}b', file=sys.stderr)
                    out_headers = {}
                    for k, v in resp.getheaders():
                        if k.lower() not in ('transfer-encoding', 'connection', 'content-encoding'):
                            out_headers[k] = v
                    self._send(status, resp_body, out_headers)
                    return

                last_status = status
                last_body = resp_body
                print(f'429 from {account_id[:8]}... (tried {len(tried)})', file=sys.stderr)
                time.sleep(0.2)
            finally:
                conn.close()

        # Exhausted all accounts
        self._send(last_status, last_body, {'Content-Type': 'application/json'})


def find_free_port(host, start=8788):
    port = start
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if s.connect_ex((host, port)) != 0:
                return port
        finally:
            s.close()
        port += 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--find-port':
        print(find_free_port(LISTEN_HOST, LISTEN_PORT))
        sys.exit(0)

    server = http.server.HTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f'Listening on http://{LISTEN_HOST}:{LISTEN_PORT}', file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down', file=sys.stderr)
