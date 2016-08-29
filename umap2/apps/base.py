'''
Umap2 applications should subclass the Umap2App.
'''
import sys
import os
import importlib
import logging
import docopt
from serial import Serial, PARITY_NONE

from umap2.phy.facedancer.max342x_phy import Max342xPhy
from umap2.phy.gadgetfs.gadgetfs_phy import GadgetFsPhy


class Umap2App(object):

    def __init__(self, docstring=None):
        if docstring is not None:
            self.options = docopt.docopt(docstring)
        else:
            self.options = {}
        self.umap_classes = [
            'audio',
            'cdc_acm',
            'ftdi',
            'hub',
            'keyboard',
            'mass_storage',
            'mtp',
            'printer',
            'smartcard',
            'vendor_specific'
        ]
        self.logger = self.get_logger()
        self.num_processed = 0
        self.fuzzer = None
        self.setup_packet_received = False

    def get_logger(self):
        levels = {
            0: logging.INFO,
            1: logging.DEBUG,
            # verbose is added by umap2.__init__ module
            2: logging.VERBOSE,
        }
        verbose = self.options.get('--verbose', 0)
        logger = logging.getLogger('umap2')
        if verbose in levels:
            logger.setLevel(levels[verbose])
        else:
            logger.setLevel(logging.VERBOSE)
        if self.options.get('--quiet', False):
            logger.setLevel(logging.WARNING)
        return logger

    def load_phy(self, phy_string):
        self.logger.info('Loading physical interface: %s' % phy_string)
        phy_arr = phy_string.split(':')
        phy_type = phy_arr[0]
        if phy_type == 'fd':
            self.logger.debug('Physical interface is facedancer')
            dev_name = phy_arr[1]
            s = Serial(dev_name, 115200, parity=PARITY_NONE, timeout=2)
            # fd = Facedancer(s)
            phy = Max342xPhy(self, s)
            return phy
        elif phy_type == 'gadgetfs':
            self.logger.debug('Physical interface is GadgetFs')
            phy = GadgetFsPhy(self)
            return phy
        raise Exception('Phy type not supported: %s' % phy_type)

    def load_device(self, dev_name, phy):
        if dev_name in self.umap_classes:
            self.logger.info('Loading USB device %s' % dev_name)
            module_name = dev_name
            module = importlib.import_module('umap2.dev.%s' % module_name)
        else:
            self.logger.info('Loading custom USB device from file: %s' % dev_name)
            dirpath, filename = os.path.split(dev_name)
            modulename = filename[:-3]
            if dirpath in sys.path:
                sys.path.remove(dirpath)
            sys.path.insert(0, dirpath)
            module = __import__(modulename, globals(), locals(), [], -1)
        usb_device = module.usb_device
        kwargs = self.get_user_device_kwargs()
        dev = usb_device(self, phy, **kwargs)
        return dev

    def get_user_device_kwargs(self):
        '''
        if user provides values for the device, get them here
        '''
        kwargs = {}
        self.update_from_user_param('--vid', 'vid', kwargs, 'int')
        self.update_from_user_param('--pid', 'pid', kwargs, 'int')
        return kwargs

    def update_from_user_param(self, flag, arg_name, kwargs, type):
        val = self.options.get(flag, None)
        if val is not None:
            if type == 'int':
                kwargs[arg_name] = int(val, 0)
                self.logger.info('Setting user-supplied %s: %#x' % (arg_name, kwargs[arg_name]))
            else:
                raise Exception('arg type not supported!!')

    def signal_setup_packet_received(self):
        '''
        Signal that we received a setup packet from the host (host is alive)
        '''
        self.setup_packet_received = True

    def should_stop_phy(self):
        '''
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

    def get_mutation(self, stage, data=None):
        '''
        mutation is only needed when fuzzing
        '''
        return None
