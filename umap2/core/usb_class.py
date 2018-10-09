# USBClass.py
#
# Contains class definition for USBClass, intended as a base class (in the OO
# sense) for implementing device classes (in the USB sense), eg, HID devices,
# mass storage devices.
from umap2.core.usb_base import USBBaseActor


class USBClass(USBBaseActor):
    name = 'Class'

    Unspecified = 0x00
    Audio = 0x01
    CDC = 0x02
    HID = 0x03
    PID = 0x05
    Image = 0x06
    Printer = 0x07
    MassStorage = 0x08
    Hub = 0x09
    CDCData = 0x0a
    SmartCard = 0x0b
    ContentSecurity = 0x0d
    Video = 0x0e
    PHDC = 0x0f
    AudioVideo = 0x10
    Billboard = 0x11
    DiagnosticDevice = 0xdc
    WirelessController = 0xe0
    Miscellaneous = 0xed
    ApplicationSpecific = 0xfe
    VendorSpecific = 0xff

    def __init__(self, app, phy):
        '''
        :param app: Umap2 application
        :param phy: Physical connection
        '''
        super(USBClass, self).__init__(app, phy)
        self.setup_request_handlers()
        self.device = None
        self.interface = None
        self.endpoint = None

    def setup_request_handlers(self):
        self.setup_local_handlers()
        self.request_handlers = {
            x: self._global_handler for x in self.local_handlers
        }

    def setup_local_handlers(self):
        self.local_handlers = {}

    def _global_handler(self, req):
        handler = self.local_handlers[req.request]
        response = handler(req)
        if response is not None:
            self.phy.send_on_endpoint(0, response)
        self.usb_function_supported('class specific setup request received')

    def default_handler(self, req):
        self._global_handler(req)
