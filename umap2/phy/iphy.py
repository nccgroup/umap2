'''
Physical interface API
'''
import logging


class PhyInterface(object):
    '''
    This class specifies the API that a physical interface should conform to
    '''

    def __init__(self, app, name):
        '''
        :type app: :class:`~umap2.app.base.Umap2App`
        :param app: application instance
        '''
        self.app = app
        self.name = name
        self.logger = logging.getLogger('umap2')
        self.stop = False
        self.connected_device = None

    def connect(self, usb_device):
        '''
        Connect a USB device

        :type usb_device: :class:`~umap2.core.usb_class.USBClass`
        :param usb_device: USB device class
        '''
        self.connected_device = usb_device

    def disconnect(self):
        '''
        Disconnect a device.
        Once this function returns, the phy doesn't have a reference to the
        device.

        :return: the disconnected device (if was connected)
        '''
        if self.connected_device:
            self.info('Disconnected device %s' % self.connected_device.name)
        else:
            self.info('Disconnect called when already disconnected')
        dev = self.connected_device
        self.connected_device = None
        return dev

    def is_connected(self):
        return self.connected_device is not None

    def send_on_endpoint(self, ep_num, data):
        '''
        Send data on a specific endpoint

        :param ep_num: number of endpoint
        :param data: data to send
        '''
        raise NotImplementedError('should be implemented in subclass')

    def stall_ep0(self):
        '''
        Stalls control endpoint (0)
        '''
        raise NotImplementedError('should be implemented in subclass')

    def run(self):
        '''
        Handle USB requests
        '''
        raise NotImplementedError('should be implemented in subclass')

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.name, msg), *args, **kwargs)
