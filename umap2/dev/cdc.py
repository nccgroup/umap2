'''
Contains class definitions to implement various USB CDC devices.

This module is incomplete, it is based on the CDC spec,
as well as CDC subclass/protocol specific specs.
The specs can be downloaded as a zip file from:
    http://www.usb.org/developers/docs/devclass_docs/CDC1.2_WMC1.1_012011.zip
'''
import struct
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface


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


class FunctionalDescriptor(USBCSInterface):
    '''
    The functional descriptors are sent as Class-Specific descriptors.
    '''
    Header = 0x00
    CM = 0x01  # Call Management Functional Descriptor.
    ACM = 0x02  # Abstract Control Management Functional Descriptor.
    DLM = 0x03  # Direct Line Management Functional Descriptor.
    TR = 0x04  # Telephone Ringer Functional Descriptor.
    TCLSRC = 0x05  # Telephone Call and Line State Reporting Capabilities Functional Descriptor.
    UN = 0x06  # Union Functional Descriptor
    CS = 0x07  # Country Selection Functional Descriptor
    TOM = 0x08  # Telephone Operational Modes Functional Descriptor
    USBT = 0x09  # USB Terminal Functional Descriptor
    NCT = 0x0A  # Network Channel Terminal Descriptor
    PU = 0x0B  # Protocol Unit Functional Descriptor
    EU = 0x0C  # Extension Unit Functional Descriptor
    MCM = 0x0D  # Multi-Channel Management Functional Descriptor
    CCM = 0x0E  # CAPI Control Management Functional Descriptor
    EN = 0x0F  # Ethernet Networking Functional Descriptor
    ATMN = 0x10  # ATM Networking Functional Descriptor
    WHCM = 0x11  # Wireless Handset Control Model Functional Descriptor
    MDLM = 0x12  # Mobile Direct Line Model Functional Descriptor
    MDLMD = 0x13  # MDLM Detail Functional Descriptor
    DMM = 0x14  # Device Management Model Functional Descriptor
    OBEX = 0x15  # OBEX Functional Descriptor
    CMDS = 0x16  # Command Set Functional Descriptor
    CMDSD = 0x17  # Command Set Detail Functional Descriptor
    TC = 0x18  # Telephone Control Model Functional Descriptor
    OBSEXSI = 0x19  # OBEX Service Identifier Functional Descriptor
    NCM = 0x1A  # NCM Functional Descriptor

    def __init__(self, app, phy, subtype, cs_config):
        name = FunctionalDescriptor.get_subtype_name(subtype)
        cs_config = struct.pack('B', subtype) + cs_config
        super(FunctionalDescriptor, self).__init__(name, app, phy, cs_config)

    @classmethod
    def get_subtype_name(cls, subtype):
        for vn in dir(cls):
            if getattr(cls, vn) == subtype:
                return vn
        return 'FunctionalDescriptor-%02x' % subtype


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
