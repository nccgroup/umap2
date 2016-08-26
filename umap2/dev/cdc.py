'''
Contains class definitions to implement various USB CDC devices.

This module is incomplete, it is based on the CDC spec,
as well as CDC subclass/protocol specific specs.
The specs can be downloaded as a zip file from:
    http://www.usb.org/developers/docs/devclass_docs/CDC1.2_WMC1.1_012011.zip
'''
import struct
from binascii import unhexlify
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.fuzz.helpers import mutable


class USBCDCClass(USBClass):
    name = 'CDCClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x20: self.handle_cdc_set_line_coding,
            0x22: self.handle_cdc_set_control_line_state,
        }

    def handle_cdc_set_line_coding(self, req):
        return b''

    def handle_cdc_set_control_line_state(self, req):
        return b''


class CommunicationClassSubclassCodes:
    '''
    Subclass codes for the communication class,
    as defined in CDC120, table 4
    '''

    Reserved = 0x00
    DirectLineControlModel = 0x01
    AbstractControlModel = 0x02
    TelephoneControlModel = 0x03
    MultiChannelControlModel = 0x04
    CapiControlModel = 0x05
    EthernetNetworkingControlModel = 0x06
    AtmNetworkingControlModel = 0x07
    WirelessHandsetControlModel = 0x08
    DeviceManagement = 0x09
    MobileDirectLineModel = 0x0a
    Obex = 0x0b
    EthernetEmulationModel = 0x0c
    NetworkControlModel = 0x0d
    # 0x0e - 0x7f - reserved (future use)
    # 0x80 - 0xfe - reserved (vendor specific)


class CommunicationClassProtocolCodes:
    '''
    Protocol codes for the communication class,
    as defined in CDC120, table 5
    '''
    NoClassSpecificProtocolRequired = 0x00
    AtCommands_v250 = 0x01
    AtCommands_Pcca101 = 0x02
    AtCommands_Pcca101AnnexO = 0x03
    AtCommands_Gsm0707 = 0x04
    AtCommands_3gpp27007 = 0x05
    AtCommands_TiaForCdma = 0x06
    EthernetEmulationModel = 0x07
    ExternalProtocol = 0xfe
    VendorSpecific = 0xff


class DataInterfaceClassProtocolCodes:
    '''
    Protocol codes for the data interface class,
    as defined in CDC120, table 7
    '''
    NoClassSpecificProtocolRequired = 0x00
    NetworkTransferBlock = 0x01
    PhysicalInterfaceProtocolForIsdnBri = 0x30
    Hdlc = 0x31
    Transparent = 0x32
    Q921M = 0x50
    Q921 = 0x51
    Q921TM = 0x52
    V42Bis = 0x90
    Q931EuroIsdn = 0x91
    V120 = 0x92
    Capi20 = 0x93
    HostBasedDriver = 0xfd
    CdcSpec = 0xfe
    VendorSpecific = 0xff


class NotificationCodes:
    NetworkConnection = 0x00
    ResponseAvailable = 0x01
    AuxJackHookState = 0x08
    RingDetect = 0x09
    SerialState = 0x20
    CallStateChange = 0x28
    LineStateChange = 0x29
    ConnectionSpeedChange = 0x2a


def management_notification(req_type, notification_code, value, index, data=None):
    '''
    Management notification structure is described (per notification) in section 6.3
    '''
    if data is None:
        data = b''
    return struct.pack('<BBHHH', req_type, notification_code, value, index, len(data)) + data


class USBCDCDevice(USBDevice):
    '''
    There are many subclasses and protocols to the USB CDC device.
    This means that we might want to implement various CDC devices.
    This class is intended for implementing only the common stuff.

    USB_CDC_ACM_DEVICE (below) is an example of concrete implementation.
    '''
    name = 'CDCDevice'
    bControlInterface = 0
    bDataInterface = 1
    bControlSubclass = CommunicationClassSubclassCodes.Reserved
    bDataSubclass = 0
    bControlProtocol = CommunicationClassProtocolCodes.NoClassSpecificProtocolRequired
    bDataProtocol = DataInterfaceClassProtocolCodes.NoClassSpecificProtocolRequired

    def __init__(self, app, phy, vid=0x2548, pid=0x1001, rev=0x0010, bmCapabilities=0x03, cs_interfaces=None, cdc_cls=None, **kwargs):
        if cs_interfaces is None:
            cs_interfaces = []
        if cdc_cls is None:
            cdc_cls = USBCDCClass(app, phy)

        super(USBCDCDevice, self).__init__(
            app=app, phy=phy,
            device_class=USBClass.CDC,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='UMAP2 NetSolutions',
            product_string='UMAP2 CDC-TRON',
            serial_number_string='UMAP2-13337-CDC',
            configurations=[
                USBConfiguration(
                    app=app, phy=phy,
                    index=1, string='Emulated CDC',
                    interfaces=[
                        # Control interface
                        USBInterface(
                            app=app, phy=phy,
                            interface_number=self.bControlInterface, interface_alternate=0,
                            interface_class=USBClass.CDC,
                            interface_subclass=self.bControlSubclass,
                            interface_protocol=self.bControlProtocol,
                            interface_string_index=0,
                            endpoints=[
                                USBEndpoint(
                                    app=app, phy=phy, number=0x3,
                                    direction=USBEndpoint.direction_in,
                                    transfer_type=USBEndpoint.transfer_type_interrupt,
                                    sync_type=USBEndpoint.sync_type_none,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=0x20,
                                    handler=self.handle_ep3_buffer_available
                                )
                            ],
                            cs_interfaces=cs_interfaces,
                            usb_class=cdc_cls
                        ),
                        USBInterface(
                            app=app, phy=phy,
                            interface_number=self.bDataInterface,
                            interface_alternate=0,
                            interface_class=USBClass.CDCData,
                            interface_subclass=self.bDataSubclass,
                            interface_protocol=self.bDataProtocol,
                            interface_string_index=0,
                            endpoints=[
                                USBEndpoint(
                                    app=app,
                                    phy=phy,
                                    number=0x1,
                                    direction=USBEndpoint.direction_out,
                                    transfer_type=USBEndpoint.transfer_type_bulk,
                                    sync_type=USBEndpoint.sync_type_none,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=0x00,
                                    handler=self.handle_ep1_data_available
                                ),
                                USBEndpoint(
                                    app=app,
                                    phy=phy,
                                    number=0x2,
                                    direction=USBEndpoint.direction_in,
                                    transfer_type=USBEndpoint.transfer_type_bulk,
                                    sync_type=USBEndpoint.sync_type_none,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=0x00,
                                    handler=self.handle_ep2_buffer_available
                                )
                            ],
                            usb_class=cdc_cls
                        )
                    ])
            ])

    #
    # default handlers
    # you should probably override them in subclass...
    #
    def handle_ep1_data_available(self, data):
        self.debug('handling %#x bytes of cdc data' % (len(data)))

    def handle_ep2_buffer_available(self):
        self.debug('ep2 buffer available')

    def handle_ep3_buffer_available(self):
        self.debug('ep3 buffer available')


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

