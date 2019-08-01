import http.server
import threading
from . import LOGGER, REGISTRY, SERVER

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = SERVER

    def log_request(self, code='-', size='-'):
        LOGGER.debug('HTTP: %s code %s', self.requestline, code)

    def log_error(self, format, *args):
        LOGGER.warn('HTTP: %s %s', self.requestline, format%args)

    def send_error(self, code, message=None, explain=None):
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.end_headers()

    def do_POST(self):
        self.protocol_version = 'HTTP/1.1'
        self.send_header('Content-Length', 0)

        path = self.path
        if not path.startswith('/device/'):
            return self.send_error(404)
        path = path[8:]

        path = path.split('/', 1)
        if len(path) != 1:
            return self.send_error(404)

        device_id = path[0]
        device = REGISTRY.find_device(device_id)
        if not device:
            return self.send_error(404, 'Device not found: ' + device_id)

        size = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(size)
        if not payload:
            return self.send_error(400, 'No payload')
        try:
            if device.transmit(payload):
                self.send_response(204, 'OK')
                self.end_headers()
                return
        except ValueError:
            pass
        self.send_error(400, 'Bad payload')

def httpd_start(port):
    if not port or port <= 0:
        LOGGER.info('HTTP server disabled')
        return False

    httpd = http.server.HTTPServer(('', port), Handler)
    httpd.request_queue_size = 10
    
    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd_thread.daemon = True
    httpd_thread.start()
    
    LOGGER.info('HTTP server started on port %s', port)
    return True