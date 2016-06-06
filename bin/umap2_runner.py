#!/usr/bin/env python
'''
USB host security assessment tool

Usage:
    umap2 detect-os -P=PHY_INFO [-v ...]
    umap2 emulate -P=PHY_INFO -C=DEVICE_CLASS [-q] [-v ...]
    umap2 fuzz -P=PHY_INFO -C=DEVICE_CLASS [-q] [-i=FUZZER_IP] [-p FUZZER_PORT] [-v ...]
    umap2 list-classes
    umap2 scan -P=PHY_INFO [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -C --class DEVICE_CLASS     class of the device or path to python file with device class
    -v --verbose                verbosity level
    -i --fuzzer-ip HOST         hostname or IP of the fuzzer [default: 127.0.0.1]
    -p --fuzzer-port PORT       port of the fuzzer [default: 26007]
    -q --quiet                  quiet mode. only print warning/error messages

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port

Examples:
    emulate keyboard without fuzzing:
        umap2 nofuzz -P fd:/dev/ttyUSB1 -C keyboard
    emulate disk-on-key with fuzzing:
        umap2 fuzz -P fd:/dev/ttyUSB1 -C mass-storage
    emulate your own device without fuzzing:
        umap2 nofuzz -P fd:/dev/ttyUSB1 -f my_usb_device.py
'''
import sys
import os
import importlib
import logging
import traceback
from docopt import docopt
from serial import Serial, PARITY_NONE

from umap2.phy.facedancer.facedancer import Facedancer
from umap2.phy.facedancer.maxusb_app import MAXUSBApp


class Umap2App(object):

    def __init__(self, options):
        self.class_mapping = {
            'audio': 'audio',
            'cdc': 'cdc',
            'ftdi': 'ftdi',
            'hub': 'hub',
            'keyboard': 'keyboard',
            'mass-storage': 'mass_storage',
            'mtp': 'mtp',
            'printer': 'printer',
            'smartcard': 'smartcard',
        }
        self.options = options
        self.logger = self.get_logger()

    def get_logger(self):
        levels = {
            0: logging.INFO,
            1: logging.DEBUG,
            # verbose is added by umap2.__init__ module
            2: logging.VERBOSE,
        }
        verbose = self.options['--verbose']
        logger = logging.getLogger('umap2')
        if verbose in levels:
            logger.setLevel(levels[verbose])
        else:
            logger.setLevel(logging.VERBOSE)
        if self.options['--quiet']:
            logger.setLevel(logging.WARNING)
        return logger

    def load_phy_app(self, phy_string, fuzzer):
        self.logger.info('loading physical interface app: %s' % phy_string)
        phy_arr = phy_string.split(':')
        phy_type = phy_arr[0]
        if phy_type == 'fd':
            self.logger.debug('physical interface is facedancer')
            dev_name = phy_arr[1]
            s = Serial(dev_name, 115200, parity=PARITY_NONE, timeout=2)
            fd = Facedancer(s)
            app = MAXUSBApp(fd, fuzzer=fuzzer)
            return app
        raise Exception('Phy type not supported: %s' % phy_type)

    def load_device(self, dev_name, app):
        if dev_name in self.class_mapping:
            self.logger.info('loading USB device %s' % dev_name)
            module_name = self.class_mapping[dev_name]
            module = importlib.import_module('umap2.dev.%s' % module_name)
        else:
            self.logger.info('loading custom USB device from file: %s' % dev_name)
            dirpath, filename = os.path.split(dev_name)
            modulename = filename[:-3]
            if dirpath in sys.path:
                sys.path.remove(dirpath)
            sys.path.insert(0, dirpath)
            module = __import__(modulename, globals(), locals(), [], -1)
        usb_device = module.usb_device
        dev = usb_device(app)
        return dev


class Umap2ListClassesApp(Umap2App):

    def run(self):
        ks = sorted(self.class_mapping.keys())
        for k in ks:
            print('%s' % k)


class Umap2DetectOSApp(Umap2App):

    def run(self):
        self.logger.error('OS detection is not implemented yet')


class Umap2ScanApp(Umap2App):

    def run(self):
        self.logger.error('Scanning is not implemented yet')


class Umap2EmulationApp(Umap2App):

    def run(self):
        fuzzer = self.get_fuzzer()
        app = self.load_phy_app(self.options['--phy'], fuzzer)
        dev = self.load_device(self.options['--class'], app)
        try:
            dev.connect()
            dev.run()
        except KeyboardInterrupt:
            self.logger.info('user terminated the run')
        except:
            self.logger.error('Got exception while connecting/running device')
            self.logger.error(traceback.format_exc())
        dev.disconnect()

    def get_fuzzer(self):
        return None


class Umap2FuzzApp(Umap2EmulationApp):

    def get_fuzzer(self):
        from kitty.remote.rpc import RpcClient
        fuzzer = RpcClient(
            host=self.options['--fuzzer-ip'],
            port=int(self.options['--fuzzer-port'])
        )
        fuzzer.start()
        return fuzzer


def _main():
    options = docopt(__doc__)
    if options['detect-os']:
        app_cls = Umap2DetectOSApp
    elif options['scan']:
        app_cls = Umap2ScanApp
    elif options['fuzz']:
        app_cls = Umap2FuzzApp
    elif options['emulate']:
        app_cls = Umap2EmulationApp
    elif options['list-classes']:
        app_cls = Umap2ListClassesApp
    app = app_cls(options)
    app.run()


if __name__ == '__main__':
    _main()
