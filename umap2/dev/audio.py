# USBAudio.py
#
# Contains class definitions to implement a USB Audio device.

import struct
from umap2.core.usb import DescriptorType
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.fuzz.helpers import mutable


class USBAudioClass(USBClass):
    name = 'AudioClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x0a: self.handle_audio_set_idle,
            0x83: self.handle_audio_get_max,
            0x82: self.handle_audio_get_min,
            0x84: self.handle_audio_get_res,
            0x81: self.handle_audio_get_cur,
            0x04: self.handle_audio_set_res,
            0x01: self.handle_audio_set_cur,
        }

    @mutable('audio_set_idle_response', silent=True)
    def handle_audio_set_idle(self, req):
        return b''

    @mutable('audio_get_max_response', silent=True)
    def handle_audio_get_max(self, req):
        return b'\x64\x00'

    @mutable('audio_get_min_response', silent=True)
    def handle_audio_get_min(self, req):
        return b'\xa0\x00'

    @mutable('audio_get_res_response', silent=True)
    def handle_audio_get_res(self, req):
        return b'\x30\x00'

    @mutable('audio_get_cur_response', silent=True)
    def handle_audio_get_cur(self, req):
        return b''

    @mutable('audio_set_res_response', silent=True)
    def handle_audio_set_res(self, req):
        return b''

    @mutable('audio_set_cur_response', silent=True)
    def handle_audio_set_cur(self, req):
        return b''


class USBAudioInterface(USBInterface):
    name = 'AudioInterface'

    def __init__(self, app, phy, int_num, usbclass, sub, proto):
        descriptors = {
            DescriptorType.hid: self.get_hid_descriptor,
            DescriptorType.report: self.get_report_descriptor
        }

        wTotalLength = 0x0047
        bInCollection = 0x02
        baInterfaceNr1 = 0x01
        baInterfaceNr2 = 0x02

        cs_config1 = [
            0x01,            # HEADER
            0x0001,          # bcdADC
            wTotalLength,    # wTotalLength
            bInCollection,   # bInCollection
            baInterfaceNr1,  # baInterfaceNr1
            baInterfaceNr2   # baInterfaceNr2
        ]

        bTerminalID = 0x01
        wTerminalType = 0x0101
        bAssocTerminal = 0x0
        bNrChannel = 0x02
        wChannelConfig = 0x0002

        cs_config2 = [
            0x02,            # INPUT_TERMINAL
            bTerminalID,     # bTerminalID
            wTerminalType,   # wTerminalType
            bAssocTerminal,  # bAssocTerminal
            bNrChannel,      # bNrChannel
            wChannelConfig,  # wChannelConfig
            0,          # iChannelNames
            0           # iTerminal
        ]

        cs_config3 = [
            0x02,       # INPUT_TERMINAL
            0x02,       # bTerminalID
            0x0201,     # wTerminalType
            0,          # bAssocTerminal
            0x01,       # bNrChannel
            0x0001,     # wChannelConfig
            0,          # iChannelNames
            0           # iTerminal
        ]

        bSourceID = 0x09

        cs_config4 = [
            0x03,       # OUTPUT_TERMINAL
            0x06,       # bTerminalID
            0x0301,     # wTerminalType
            0,          # bAssocTerminal
            bSourceID,  # bSourceID
            0           # iTerminal
        ]

        cs_config5 = [
            0x03,       # OUTPUT_TERMINAL
            0x07,       # bTerminalID
            0x0101,     # wTerminalType
            0,          # bAssocTerminal
            0x0a,       # bSourceID
            0           # iTerminal
        ]

        bUnitID = 0x09
        bSourceID = 0x01
        bControlSize = 0x01
        bmaControls0 = 0x01
        bmaControls1 = 0x02
        bmaControls2 = 0x02

        cs_config6 = [
            0x06,           # FEATURE_UNIT
            bUnitID,        # bUnitID
            bSourceID,      # bSourceID
            bControlSize,   # bControlSize
            bmaControls0,   # bmaControls0
            bmaControls1,   # bmaControls1
            bmaControls2,   # bmaControls2
            0               # iFeature
        ]

        cs_config7 = [
            0x06,       # FEATURE_UNIT
            0x0a,       # bUnitID
            0x02,       # bSourceID
            0x01,       # bControlSize
            0x43,       # bmaControls0
            0x00,       # bmaControls1
            0x00,       # bmaControls2
            0           # iFeature
        ]

        cs_interfaces0 = [
            USBCSInterface(app, phy, cs_config1, 1, 1, 0),
            USBCSInterface(app, phy, cs_config2, 1, 1, 0),
            USBCSInterface(app, phy, cs_config3, 1, 1, 0),
            USBCSInterface(app, phy, cs_config4, 1, 1, 0),
            USBCSInterface(app, phy, cs_config5, 1, 1, 0),
            USBCSInterface(app, phy, cs_config6, 1, 1, 0),
            USBCSInterface(app, phy, cs_config7, 1, 1, 0)
        ]

        # cs_config8 = [
        #     0x01,       # AS_GENERAL
        #     0x01,       # bTerminalLink
        #     0x01,       # bDelay
        #     0x0001      # wFormatTag
        # ]

        # cs_config9 = [
        #     0x02,       # FORMAT_TYPE
        #     0x01,       # bFormatType
        #     0x02,       # bNrChannels
        #     0x02,       # bSubframeSize
        #     0x10,       # bBitResolution
        #     0x02,       # SamFreqType
        #     0x80bb00,    # tSamFreq1
        #     0x44ac00    # tSamFreq2
        # ]

        cs_interfaces1 = []
        cs_interfaces2 = []
        cs_interfaces3 = []

        # ep_cs_config1 = [
        #     0x01,       # EP_GENERAL
        #     0x01,       # Endpoint number
        #     0x01,       # bmAttributes
        #     0x01,       # bLockDelayUnits
        #     0x0001,     # wLockeDelay
        # ]

        endpoints0 = [
            USBEndpoint(
                app=app,
                phy=phy,
                number=2,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_interrupt,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0x02,
                handler=self.audio_ep2_buffer_available
            )
        ]

        if int_num == 3:
            endpoints = endpoints0
        else:
            endpoints = []

        if int_num == 0:
            cs_interfaces = cs_interfaces0
        if int_num == 1:
            cs_interfaces = cs_interfaces1
        if int_num == 2:
            cs_interfaces = cs_interfaces2
        if int_num == 3:
            cs_interfaces = cs_interfaces3

        # if self.int_num == 1:
        #     endpoints = endpoints1

        # TODO: un-hardcode string index
        super(USBAudioInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=endpoints,
            descriptors=descriptors,
            cs_interfaces=cs_interfaces,
            device_class=USBAudioClass(app, phy)
        )

    def audio_ep2_buffer_available(self):
        return self.send_on_endpoint(2, b'\x00\x00\x00')

    @mutable('audio_hid_descriptor')
    def get_hid_descriptor(self, *args, **kwargs):
        report_desc = self.get_report_descriptor()
        report_desc_len = struct.pack('<H', len(report_desc))
        return b'\x09\x21\x10\x01\x00\x01\x22' + report_desc_len

    @mutable('audio_report_descriptor')
    def get_report_descriptor(self, *args, **kwargs):
        return(
            b'\x05\x0C\x09\x01\xA1\x01\x15\x00\x25\x01\x09\xE9\x09\xEA\x75' +
            b'\x01\x95\x02\x81\x02\x09\xE2\x09\x00\x81\x06\x05\x0B\x09\x20' +
            b'\x95\x01\x81\x42\x05\x0C\x09\x00\x95\x03\x81\x02\x26\xFF\x00' +
            b'\x09\x00\x75\x08\x95\x03\x81\x02\x09\x00\x95\x04\x91\x02\xC0'
        )


class USBAudioDevice(USBDevice):
    name = 'AudioDevice'

    def __init__(self, app, phy, vid=0x041e, pid=0x0402, rev=0x0001, **kwargs):
        super(USBAudioDevice, self).__init__(
            app=app,
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Creative Technology Ltd.',
            product_string='Creative HS-720 Headset',
            serial_number_string='',
            configurations=[
                USBConfiguration(
                    app=app,
                    phy=phy,
                    index=1,
                    string='Emulated Audio',
                    interfaces=[
                        USBAudioInterface(app, phy, 0, USBClass.Audio, 0x01, 0x00),
                        USBAudioInterface(app, phy, 1, USBClass.Audio, 0x02, 0x00),
                        USBAudioInterface(app, phy, 2, USBClass.Audio, 0x02, 0x00),
                        USBAudioInterface(app, phy, 3, USBClass.HID, 0x00, 0x00),
                    ]
                )
            ],
        )


usb_device = USBAudioDevice
