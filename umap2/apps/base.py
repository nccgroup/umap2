'''
Umap2 applications should subclass the Umap2App.
'''
import sys
import os
import importlib
import logging
import docopt
from serial import Serial, PARITY_NONE

from umap2.phy.facedancer.facedancer import Facedancer
from umap2.phy.facedancer.maxusb_app import MAXUSBApp


class Umap2App(object):

    def __init__(self, docstring):
        self.options = docopt.docopt(docstring)
        self.umap_classes = [
            'audio',
            'cdc',
            'ftdi',
            'hub',
            'keyboard',
            'mass_storage',
            'mtp',
            'printer',
            'smartcard',
        ]
        self.logger = self.get_logger()
        self.num_processed = 0

    def get_logger(self):
        levels = {
            0: logging.INFO,
            1: logging.DEBUG,
            # verbose is added by umap2.__init__ module
            2: logging.VERBOSE,
        }
        if '--verbose' in self.options:
            verbose = self.options['--verbose']
        else:
            verbose = 0
        logger = logging.getLogger('umap2')
        if verbose in levels:
            logger.setLevel(levels[verbose])
        else:
            logger.setLevel(logging.VERBOSE)
        if '--quiet' in self.options and self.options['--quiet']:
            logger.setLevel(logging.WARNING)
        return logger

    def load_phy(self, phy_string, fuzzer):
        self.logger.info('loading physical interface: %s' % phy_string)
        phy_arr = phy_string.split(':')
        phy_type = phy_arr[0]
        if phy_type == 'fd':
            self.logger.debug('physical interface is facedancer')
            dev_name = phy_arr[1]
            s = Serial(dev_name, 115200, parity=PARITY_NONE, timeout=2)
            fd = Facedancer(s)
            phy = MAXUSBApp(fd, self, fuzzer=fuzzer)
            return phy
        raise Exception('phy type not supported: %s' % phy_type)

    def load_device(self, dev_name, phy):
        if dev_name in self.umap_classes:
            self.logger.info('loading USB device %s' % dev_name)
            module_name = dev_name
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
        dev = usb_device(phy)
        return dev

    def packet_processed(self):
        '''
        Callback from phy after processing of each packet
        :return: whether phy should stop serving.
        '''
        return False

    def usb_function_supported(self):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.
        By default, do nothing with this information
        '''
        pass
