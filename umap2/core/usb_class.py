# USBClass.py
#
# Contains class definition for USBClass, intended as a base class (in the OO
# sense) for implementing device classes (in the USB sense), eg, HID devices,
# mass storage devices.
from umap2.core.usb_base import USBBaseActor


class USBClass(USBBaseActor):
    name = "generic USB device class"

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

    # maps bRequest to handler function
    request_handlers = {}

    def __init__(self, app):
        super(USBClass, self).__init__(app)
        self.interface = None
        self.setup_request_handlers()

    def set_interface(self, interface):
        self.interface = interface

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
            self.app.send_on_endpoint(0, response)
        self.usb_function_supported()
