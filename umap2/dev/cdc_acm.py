'''
Implement a Communication Device Class (CDC) Abstract Control Class (ACM)
device.
The specification for this device may be found in CDC120-20101113-track.pdf
and in PSTN120.pdf.
'''
import struct
from binascii import unhexlify
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.dev.cdc import USBCDCClass
from umap2.dev.cdc import USBCDCDevice
from umap2.dev.cdc import CommunicationClassSubclassCodes
from umap2.dev.cdc import CommunicationClassProtocolCodes
from umap2.dev.cdc import DataInterfaceClassProtocolCodes
from umap2.dev.cdc import NotificationCodes
from umap2.dev.cdc import management_notification
from umap2.fuzz.helpers import mutable


class USB_CDC_ACM_Class(USBCDCClass):
    name = 'USB CDC Comm Class'

    def __init__(self, app, phy):
        super(USB_CDC_ACM_Class, self).__init__(app, phy)
        self.encapsulated_response = b''

    def setup_local_handlers(self):
        super(USB_CDC_ACM_Class, self).setup_local_handlers()
        self.local_handlers.update({
            0x00: self.handle_send_encapsulated_command,
            0x01: self.handle_get_encapsulated_response
            # rest of the requests are optional
        })

    def handle_send_encapsulated_command(self, req):
        self.encapsulated_command = req.data
        return b''

    @mutable('cdc_acm_get_encapsulated_response')
    def handle_get_encapsulated_response(self, req):
        return self.encapsulated_response


class USB_CDC_ACM_DEVICE(USBCDCDevice):

    name = 'CDC ACM Device'

    bControlSubclass = CommunicationClassSubclassCodes.AbstractControlModel
    bControlProtocol = CommunicationClassProtocolCodes.AtCommands_v250
    bDataProtocol = DataInterfaceClassProtocolCodes.NoClassSpecificProtocolRequired

    def __init__(self, app, phy, vid=0x2548, pid=0x1001, rev=0x0010, bmCapabilities=0x01, cs_interfaces=None, cdc_cls=None, **kwargs):
        cdc_cls = USB_CDC_ACM_Class(app, phy)
        cs_interfaces = [
            # Header Functional Descriptor
            USBCSInterface('Header', app, phy, '\x00\x01\x01'),
            # Call Management Functional Descriptor
            USBCSInterface('CMF', app, phy, struct.pack('BBB', 1, bmCapabilities, USBCDCDevice.bDataInterface)),
            USBCSInterface('ACMF1', app, phy, struct.pack('BB', 2, bmCapabilities)),
            USBCSInterface('ACMF2', app, phy, struct.pack('BBB', 6, USBCDCDevice.bControlInterface, USBCDCDevice.bDataInterface)),
        ]
        super(USB_CDC_ACM_DEVICE, self).__init__(app, phy, vid, pid, rev, bmCapabilities=0x03, cs_interfaces=cs_interfaces, cdc_cls=cdc_cls, **kwargs)
        self.receive_buffer = b''

    def handle_ep1_data_available(self, data):
        '''
        print the AT commands only upon new line
        '''
        self.receive_buffer += data
        if b'\r' in self.receive_buffer:
            lines = self.receive_buffer.split(b'\r')
            self.receive_buffer = lines[-1]
            for l in lines[:-1]:
                self.info('received line: %s' % l)

    def handle_ep2_buffer_available(self):
        # send ARP
        self.debug('in handle ep2 buffer available')
        self.send_on_endpoint(
            2,
            unhexlify('ffffffffffffaabbccddeeff08060001080006040001600308aaaaaac0a80065000000000000c0a80100')
        )

    def handle_ep3_buffer_available(self):
        '''
        management notification endpoint...
        '''
        self.debug('sending network connection notification')
        resp = management_notification(0xa1, NotificationCodes.NetworkConnection, 1, self.bDataInterface)
        self.send_on_endpoint(3, resp)


usb_device = USB_CDC_ACM_DEVICE
