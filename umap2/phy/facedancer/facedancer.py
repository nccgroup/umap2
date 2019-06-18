'''
Facedancer protocol implementation, used by Max342xPhy
'''
import struct
from binascii import hexlify
import logging


class Facedancer(object):

    def __init__(self, serialport):
        self.serialport = serialport
        self.logger = logging.getLogger('umap2')
        self.reset()

    def halt(self):
        self.serialport.setRTS(1)
        self.serialport.setDTR(1)

    def reset(self, count=10):
        self.logger.info('Facedancer resetting...')
        for i in range(count):
            self.halt()
            self.serialport.setDTR(0)
            rsp_data = self.read(1024)
            if len(rsp_data) < 4:
                continue
            app, verb, n = struct.unpack('<BBH', rsp_data[:4])
            if verb == 0x7f and n == (len(rsp_data) - 4):
                self.logger.debug("No buffer any more")
                self.logger.info("Facedancer reset")
                return
        raise Exception("Facedancer reset fault.")

    def read(self, n):
        '''Read raw bytes.'''
        b = self.serialport.read(n)
        self.logger.verbose('Facedancer received %s bytes; %s bytes remaining' % (len(b), self.serialport.inWaiting()))
        self.logger.verbose('Facedancer Rx: %s' % hexlify(b))
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
        self.logger.verbose('Facedancer Rx command: %s' % cmd)
        return cmd

    def write(self, b):
        '''Write raw bytes.'''
        self.logger.verbose('Facedancer Tx: %s' % hexlify(b))
        self.serialport.write(b)

    def writecmd(self, c):
        '''Write a single command.'''
        self.write(c.as_bytestring())
        self.logger.verbose('Facedancer Tx command: %s' % c)


class FacedancerCommand(object):
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
