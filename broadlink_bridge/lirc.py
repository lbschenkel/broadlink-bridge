import socketserver
import threading
from . import LOGGER, REGISTRY, SERVER

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        while(True):
            self.line = self.readline()
            self.line = self.line.decode('UTF-8')
            if not self.line:
                break
            parsed = self.line.split(' ', 1)
            command = parsed[0]
            args = None
            if len(parsed) > 1:
                args = parsed[1]
            self.handle_command(command, args)

    def readline(self):
       line = self.rfile.readline()
       line = line.strip()
       return line

    def reply(self, success=True, data=None):
        self.writeline('BEGIN')
        self.writeline(self.line)
        self.writeline('SUCCESS' if success else 'ERROR')
        if data:
            self.writeline('DATA')
            self.writeline(str(len(data)))
            for line in data:
                self.writeline(line)
        self.writeline('END')
   
    def write(self, data):
        if isinstance(data, str):
            data = data.encode('UTF-8')
        self.wfile.write(data)
        return self
    
    def writeline(self, line):
        self.write(line).write(b'\n').wfile.flush()

    def handle_command(self, command, args):
        if command == 'VERSION':
            self.reply(True, [SERVER])
            return
        elif command == 'LIST':
            if not args:
                self.reply(True, [str(dev.host) for dev in REGISTRY.get_devices()])
            else:
                self.reply(True, REGISTRY.get_commands())
            return
        elif command == 'SEND_ONCE':
            if args:
                payload   = args.split(' ')
                device_id = payload[0]
                command   = payload[1]
                repeat    = int(payload[2]) if len(payload) > 2 else None
                
                device  = REGISTRY.find_device(device_id)
                if device and command:
                    try:
                        device.transmit(command, repeat)
                        self.reply()
                        return
                    except ValueError:
                        pass
        elif command == 'SEND_CCF_ONCE':
            if args:
                payload = args.split(' ', 1)
                repeat  = int(payload[0])
                payload = payload[1]
                try:
                    device = REGISTRY.find_device('default')
                    if device:
                        device.transmit(payload, repeat=repeat)
                        self.reply()
                        return
                except ValueError:
                    pass
        self.reply(False)

class Server(socketserver.TCPServer):
    def handle_error(self, request, client_address):
        super().handle_error(request, client_address)

def lircd_start(port):
    if not port or port <= 0:
        LOGGER.info('LIRC server disabled')
        return False
    
    lircd = Server(('', port), Handler, bind_and_activate=False)
    lircd.allow_reuse_address = True
    lircd.server_bind()
    lircd.server_activate()
    
    lircd_thread = threading.Thread(target=lircd.serve_forever)
    lircd_thread.daemon = True
    lircd_thread.start()

    LOGGER.info('LIRC server started on port %s', port)
    return True