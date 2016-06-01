# Facedancer.py
#
# Contains class definitions for Facedancer, FacedancerCommand, FacedancerApp,
# and GoodFETMonitorApp.
import struct
from binascii import hexlify
import logging


class Facedancer:

    def __init__(self, serialport):
        self.serialport = serialport
        self.logger = logging.getLogger('umap2')
        self.reset()
        self.monitor_app = GoodFETMonitorApp(self)
        self.monitor_app.announce_connected()

    def halt(self):
        self.serialport.setRTS(1)
        self.serialport.setDTR(1)

    def reset(self):
        self.logger.info('Facedancer resetting...')
        self.halt()
        self.serialport.setDTR(0)
        self.readcmd()
        self.logger.info('Facedancer reset')

    def read(self, n):
        '''Read raw bytes.'''
        b = self.serialport.read(n)
        self.logger.debug('Facedancer received %s bytes; %s bytes remaining' % (len(b), self.serialport.inWaiting()))
        self.logger.debug('Facedancer Rx: %s' % hexlify(b))
        return b

    def readcmd(self):
        '''Read a single command.'''

        b = self.read(4)
        app, verb, n = struct.unpack('<BBH', b)

        if n > 0:
            data = self.read(n)
        else:
            data = b''

        if len(data) != n:
            raise ValueError('Facedancer expected %d bytes but received only %d' % (n, len(data)))
        cmd = FacedancerCommand(app, verb, data)
        self.logger.debug('Facedancer Rx command: %s' % cmd)
        return cmd

    def write(self, b):
        '''Write raw bytes.'''
        self.logger.debug('Facedancer Tx: %s' % hexlify(b))
        self.serialport.write(b)

    def writecmd(self, c):
        '''Write a single command.'''
        self.write(c.as_bytestring())
        self.logger.debug('Facedancer Tx command: %s' % c)


class FacedancerCommand:
    def __init__(self, app=None, verb=None, data=None):
        self.app = app
        self.verb = verb
        self.data = data

    def __str__(self):
        s = 'app 0x%02x, verb 0x%02x, len %d' % (self.app, self.verb, len(self.data))

        if len(self.data) > 0:
            s += ', data %s' % hexlify(self.data)

        return s

    def long_string(self):
        s = 'app: %s\nverb: %s\nlen: %s' % (self.app, self.verb, len(self.data))

        if len(self.data) > 0:
            try:
                s += '\n' + self.data.decode('utf-8')
            except UnicodeDecodeError:
                s += '\n' + hexlify(self.data)

        return s

    def as_bytestring(self):
        b = struct.pack('<BBH', self.app, self.verb, len(self.data)) + self.data
        return b


class FacedancerApp:
    app_name = 'override this'
    app_num = 0x00

    def __init__(self, device):
        self.device = device
        self.logger = logging.getLogger('umap2')
        self.init_commands()
        self.info('initialized')

    def init_commands(self):
        pass

    def enable(self):
        for i in range(3):
            self.device.writecmd(self.enable_app_cmd)
            self.device.readcmd()

        self.info('enabled')

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.app_name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.app_name, msg), *args, **kwargs)


class GoodFETMonitorApp(FacedancerApp):
    app_name = 'GoodFET monitor'
    app_num = 0x00

    def read_byte(self, addr):
        d = [addr & 0xff, addr >> 8]
        cmd = FacedancerCommand(0, 2, d)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()

        return struct.unpack('<B', resp.data[0:1])[0]

    def get_infostring(self):
        return struct.pack('<BB', self.read_byte(0xff0), self.read_byte(0xff1))

    def get_clocking(self):
        return struct.pack('<BB', self.read_byte(0x57), self.read_byte(0x56))

    def print_info(self):
        infostring = self.get_infostring()
        clocking = self.get_clocking()

        self.info('MCU: %s' % hexlify(infostring))
        self.info('clocked at %s' % hexlify(clocking))

    def list_apps(self):
        cmd = FacedancerCommand(self.app_num, 0x82, b'0x0')
        self.device.writecmd(cmd)

        resp = self.device.readcmd()
        self.info('build date: %s' % resp.data.decode('utf-8'))
        self.info('firmware apps:')
        while True:
            resp = self.device.readcmd()
            if len(resp.data) == 0:
                break
            self.info(resp.data.decode('utf-8'))

    def announce_connected(self):
        cmd = FacedancerCommand(self.app_num, 0xb1, b'')
        self.device.writecmd(cmd)
        self.device.readcmd()
