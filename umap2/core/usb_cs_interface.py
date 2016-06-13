# USBCSInterface.py
#
# Contains class definition for USBCSInterface.
import struct
from umap2.core.usb import DescriptorType
from umap2.core.usb_base import USBBaseActor
from umap2.core.usb_class import USBClass
from umap2.fuzz.helpers import mutable


class USBCSInterface(USBBaseActor):
    name = 'CSInterface'

    def __init__(self, app, phy, cs_config, usbclass, sub, proto, descriptors=None):
        '''
        :param app: umap2 application
        :param phy: physical connection
        :param cs_config: class specific configuration
        :param usbclass: the interface's class
        :param sub: the interface's subclass
        :param proto: the interface's protocol
        :param descriptors: dictionary of descriptors or descriptor handlers (default: None)
        '''
        super(USBCSInterface, self).__init__(app, phy)
        self.usbclass = usbclass
        self.sub = sub
        self.proto = proto
        self.cs_config = cs_config
        self.descriptors = descriptors if descriptors else {}
        self.descriptors[DescriptorType.cs_interface] = self.get_descriptor

        self.request_handlers = {
            0x06: self.handle_get_descriptor_request,
            0x0b: self.handle_set_interface_request
        }

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    def handle_get_descriptor_request(self, req):
        dtype = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang = req.index
        n = req.length

        response = None

        self.info((
            'received GET_DESCRIPTOR req %d, index %d, language 0x%04x, length %d'
        ) % (dtype, dindex, lang, n))

        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.phy.send_on_endpoint(0, response[:n])
            self.verbose('sent %d bytes in response' % (n))

    def handle_set_interface_request(self, req):
        self.info('received SET_INTERFACE request')
        self.phy.stall_ep0()

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    @mutable('usbcsinterface_descriptor')
    def get_descriptor(self):
        d = b''
        # ######################## CDC class ###############################
        if self.usbclass == USBClass.CDC:
            if self.cs_config[0] == 0x00:
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x00  # Header Functional Descriptor
                bcdCDC = self.cs_config[1]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    (bcdCDC >> 8) & 0xff,
                    bcdCDC & 0xff,
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            if self.cs_config[0] == 0x01:
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x01  # Call Management Functional Descriptor
                bmCapabilities = self.cs_config[1]
                bDataInterface = self.cs_config[2]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bmCapabilities,
                    bDataInterface
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            if self.cs_config[0] == 0x02:
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x02  # Abstract Control Management Functional Descriptor
                bmCapabilities = self.cs_config[1]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bmCapabilities
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            if self.cs_config[0] == 0x06:
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x06  # Abstract Control Management Functional Descriptor
                bControlInterface = self.cs_config[1]
                bSubordinateInterface = self.cs_config[2]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bControlInterface,
                    bSubordinateInterface
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            if (self.cs_config[0] == 0x0f) and (self.sub == 6):
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x0f  # Ethernet Networking Functional Descriptor
                iMACAddress = self.cs_config[1]
                bmEthernetStatistics = self.cs_config[2]
                wMaxSegmentSize = self.cs_config[3]
                wNumberMCFilters = self.cs_config[4]
                bNumberPowerFilters = self.cs_config[5]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    iMACAddress,
                    (bmEthernetStatistics >> 24) & 0xff,
                    (bmEthernetStatistics >> 16) & 0xff,
                    (bmEthernetStatistics >> 8) & 0xff,
                    bmEthernetStatistics & 0xff,
                    (wMaxSegmentSize >> 8) & 0xff,
                    wMaxSegmentSize & 0xff,
                    (wNumberMCFilters >> 8) & 0xff,
                    wNumberMCFilters & 0xff,
                    bNumberPowerFilters
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
        # ######################### Audio class #########################
        if (self.usbclass == USBClass.Audio) and (self.sub == 1) and (self.proto == 0):
            if self.cs_config[0] == 0x01:  # HEADER
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x01  # HEADER
                bcdADC = self.cs_config[1]
                wTotalLength = self.cs_config[2]
                bInCollection = self.cs_config[3]
                baInterfaceNr1 = self.cs_config[4]
                baInterfaceNr2 = self.cs_config[5]  # HACK: hardcoded number of interface
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    (bcdADC >> 8) & 0xff,
                    bcdADC & 0xff,
                    wTotalLength & 0xff,
                    (wTotalLength >> 8) & 0xff,
                    bInCollection,
                    baInterfaceNr1,
                    baInterfaceNr2
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            elif self.cs_config[0] == 0x02:  # INPUT_TERMINAL
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x02  # INPUT_TERMINAL
                bTerminalID = self.cs_config[1]
                wTerminalType = self.cs_config[2]
                bAssocTerminal = self.cs_config[3]  # ID of associated output terminal
                bNrChannels = self.cs_config[4]  # number of logical output channels
                wChannelConfig = self.cs_config[5]  # spatial location of logical channels: Left front/Right front
                iChannelNames = self.cs_config[6]  # Index of String descriptor describing name of logical channel
                iTerminal = self.cs_config[7]  # Index of String descriptor describing input terminal
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalID,
                    wTerminalType & 0xff,
                    (wTerminalType >> 8) & 0xff,
                    bAssocTerminal,
                    bNrChannels,
                    wChannelConfig & 0xff,
                    (wChannelConfig >> 8) & 0xff,
                    iChannelNames,
                    iTerminal
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            elif self.cs_config[0] == 0x03:  # OUTPUT_TERMINAL
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x03  # OUTPUT_TERMINAL
                bTerminalID = self.cs_config[1]
                wTerminalType = self.cs_config[2]
                bAssocTerminal = self.cs_config[3]  # ID of associated output terminal
                bSourceID = self.cs_config[4]  # ID of the terminal to which this terminal is connected
                iTerminal = self.cs_config[5]  # Index of String descriptor describing input terminal
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalID,
                    wTerminalType & 0xff,
                    (wTerminalType >> 8) & 0xff,
                    bAssocTerminal,
                    bSourceID,
                    iTerminal
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            elif self.cs_config[0] == 0x06:  # FEATURE_UNIT
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x06  # FEATURE_UNIT
                bUnitID = self.cs_config[1]
                bsourceID = self.cs_config[2]
                bControlSize = self.cs_config[3]
                bmaControls0 = self.cs_config[4]
                bmaControls1 = self.cs_config[5]
                bmaControls2 = self.cs_config[6]
                iFeature = self.cs_config[7]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bUnitID,
                    bsourceID,
                    bControlSize,
                    bmaControls0,
                    bmaControls1,
                    bmaControls2,
                    iFeature
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
        elif (self.usbclass == 1) and (self.sub == 2) and (self.proto == 0):
            if self.cs_config[0] == 0x01:  # AS_GENERAL
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x01  # AS_GENERAL
                bTerminalLink = self.cs_config[1]
                bDelay = self.cs_config[2]
                wFormatTag = self.cs_config[3]
                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bTerminalLink,
                    bDelay,
                    wFormatTag & 0xff,
                    (wFormatTag >> 8) & 0xff,
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
            elif self.cs_config[0] == 0x02:  # FORMAT_TYPE
                bDescriptorType = 36  # CS_INTERFACE
                bDescriptorSubtype = 0x02  # FORMAT_TYPE
                bFormatType = self.cs_config[1]
                bNrChannels = self.cs_config[2]
                bSubFrameSize = self.cs_config[3]
                bBitResolution = self.cs_config[4]
                bSamFreqType = self.cs_config[5]
                tSamFreq1 = self.cs_config[6]
                tSamFreq2 = self.cs_config[7]

                d = bytearray([
                    bDescriptorType,
                    bDescriptorSubtype,
                    bFormatType,
                    bNrChannels,
                    bSubFrameSize,
                    bBitResolution,
                    bSamFreqType,
                    (tSamFreq1 >> 16) & 0xff,
                    (tSamFreq1 >> 8) & 0xff,
                    tSamFreq1 & 0xff,
                    (tSamFreq2 >> 16) & 0xff,
                    (tSamFreq2 >> 8) & 0xff,
                    tSamFreq2 & 0xff
                ])
                config_length = struct.pack('<B', len(d) + 1)
                d = config_length + d
        # ############################ end Audio class ##########################################
        return d
