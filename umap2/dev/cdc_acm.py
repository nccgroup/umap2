'''
Implement a Communication Device Class (CDC) Abstract Control Class (ACM)
device.
The specification for this device may be found in CDC120-20101113-track.pdf
and in PSTN120.pdf.
'''
import struct
from binascii import unhexlify
from umap2.dev.cdc import USBCDCClass
from umap2.dev.cdc import USBCDCDevice
from umap2.dev.cdc import CommunicationClassSubclassCodes
from umap2.dev.cdc import CommunicationClassProtocolCodes
from umap2.dev.cdc import DataInterfaceClassProtocolCodes
from umap2.dev.cdc import FunctionalDescriptor as FD


class USB_CDC_ACM_DEVICE(USBCDCDevice):

    name = 'CDC ACM Device'

    bControlSubclass = CommunicationClassSubclassCodes.AbstractControlModel
    bControlProtocol = CommunicationClassProtocolCodes.AtCommands_v250
    bDataProtocol = DataInterfaceClassProtocolCodes.NoClassSpecificProtocolRequired

    def __init__(self, app, phy, vid=0x2548, pid=0x1001, rev=0x0010, bmCapabilities=0x01, cs_interfaces=None, cdc_cls=None, **kwargs):
        cdc_cls = USBCDCClass(app, phy)
        cs_interfaces = [
            # Header Functional Descriptor
            FD(app, phy, FD.Header, '\x01\x01'),
            # Call Management Functional Descriptor
            FD(app, phy, FD.CM, struct.pack('BB', bmCapabilities, USBCDCDevice.bDataInterface)),
            FD(app, phy, FD.ACM, struct.pack('B', bmCapabilities)),
            FD(app, phy, FD.UN, struct.pack('BB', USBCDCDevice.bControlInterface, USBCDCDevice.bDataInterface)),
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


usb_device = USB_CDC_ACM_DEVICE
