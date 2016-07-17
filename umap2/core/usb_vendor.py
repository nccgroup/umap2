# USBVendor.py
#
# Contains class definition for USBVendor, intended as a base class (in the OO
# sense) for implementing device vendors.
from umap2.core.usb_base import USBBaseActor


class USBVendor(USBBaseActor):
    name = 'DeviceVendor'

    # maps bRequest to handler function
    request_handlers = {}

    def __init__(self, app, phy):
        '''
        :param app: umap2 application
        :param phy: physical connection
        :param device: the usb device
        '''
        super(USBVendor, self).__init__(app, phy)
        self.setup_request_handlers()
        self.device = None
        self.interface = None
        self.endpoint = None

    def setup_request_handlers(self):
        self.setup_local_handlers()
        self.request_handlers = {
            x: self.handle_all for x in self.local_handlers
        }

    def setup_local_handlers(self):
        self.local_handlers = {}

    def handle_all(self, req):
        handler = self.local_handlers[req.request]
        response = handler(req)
        if response is not None:
            self.phy.send_on_endpoint(0, response)
        self.usb_function_supported()
