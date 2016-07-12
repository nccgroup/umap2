'''
Clean implementation of audio device

Based on:

  - http://www.usb.org/developers/docs/devclass_docs/audio10.pdf

The specific parameters of this implementation is based on a SilverLine
headset.
However, it does not contain alternate settings for the interfaces
and no HID interface (as we don't really need it here)
'''
from six.moves.queue import Queue
from umap2.core.usb_class import USBClass
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_cs_endpoint import USBCSEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.core.usb_device import USBDevice
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_interface import USBInterface
from umap2.fuzz.helpers import mutable


SUBCLASS_UNDEFINED = 0x00
SUBCLASS_AUDIOCONTROL = 0x01
SUBCLASS_AUDIOSTREAMING = 0x02
SUBCLASS_MIDISTREAMING = 0x03


class USBAudioClass(USBClass):
    name = 'AudioClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x01: self.handle_audio_set_cur,
            0x04: self.handle_audio_set_res,
            0x0a: self.handle_audio_set_idle,
            0x81: self.handle_audio_get_cur,
            0x82: self.handle_audio_get_min,
            0x83: self.handle_audio_get_max,
            0x84: self.handle_audio_get_res,
        }
        self._settings = {
            # (val, index): [cur, min, max, res, (idle)]
            (0x0100, 0x0001): ['\x44\xac\x00', '\x44\xac\x00', '\x80\xbb\x00', '\x80\xbb\x00'],
            # (0x0100, 0x0002): ['\x44\xac\x00', '\x44\xac\x00', '\x80\xbb\x00', '\x80\xbb\x00'],
            (0x0100, 0x0082): ['\x44\xac\x00', '\x44\xac\x00', '\x80\xbb\x00', '\x80\xbb\x00'],
            (0x0100, 0x0900): ['\x00', '\x00', '\xff', '\x00'],
            (0x0100, 0x0a00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0100, 0x0d00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0101, 0x0f00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0102, 0x0f00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0200, 0x0a00): ['\x00\x00', '\x00\x00', '\xd0\x17', '\x30\x00', '\x00\x00'],
            (0x0200, 0x0d00): ['\x80\x22', '\x00\x00', '\xd0\x2f', '\x30\x00'],
            (0x0201, 0x0900): ['\x80\x22', '\xa0\xe3', '\xf0\xff', '\x30\x00'],
            (0x0201, 0x0f00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0202, 0x0900): ['\xcf\x00', '\x00\x00', '\xcf\x00', '\x30\x00'],
            (0x0202, 0x0f00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0301, 0x0f00): ['\x01', '\x00', '\xff', '\x00'],
            (0x0302, 0x0f00): ['\x00\x00', '\x00\x00', '\x00\x00', '\x00\x00'],
            (0x0700, 0x0a00): ['\x01', '\x00', '\xff', '\x00'],
        }

        self._cur = b'\x44\xac\x00'
        self._res = b'\x30\x00'
        self._min = b'\x00\x20'
        self._max = b'\x00\x21'
        self._idle = b''

    def set_param_val(self, req, param):
        try:
            self._settings[(req.value, req.index)][param] = req.data
        except:
            raise Exception('Cannot find tuple (%#x, %#x, %#x) in settings' % (req.value, req.index, param))

    def get_param_val(self, req, param):
        try:
            return self._settings[(req.value, req.index)][param]
        except:
            raise Exception('Cannot find tuple (%#x, %#x, %#x) in settings' % (req.value, req.index, param))

    @mutable('audio_set_cur_response', silent=True)
    def handle_audio_set_cur(self, req):
        self.set_param_val(req, 0)
        return b''

    @mutable('audio_set_res_response', silent=True)
    def handle_audio_set_res(self, req):
        self.set_param_val(req, 3)
        return b''

    @mutable('audio_set_idle_response', silent=True)
    def handle_audio_set_idle(self, req):
        self.set_param_val(req, 4)
        return b''

    @mutable('audio_get_cur_response', silent=True)
    def handle_audio_get_cur(self, req):
        return self.get_param_val(req, 0)

    @mutable('audio_get_min_response', silent=True)
    def handle_audio_get_min(self, req):
        return self.get_param_val(req, 1)

    @mutable('audio_get_max_response', silent=True)
    def handle_audio_get_max(self, req):
        return self.get_param_val(req, 2)

    @mutable('audio_get_res_response', silent=True)
    def handle_audio_get_res(self, req):
        return self.get_param_val(req, 3)


class AudioStreaming(object):

    def __init__(self, app, phy, tx_ep, rx_ep):
        self.app = app
        self.phy = phy
        self.tx_ep = tx_ep
        self.rx_ep = rx_ep
        self.txq = Queue()

    def buffer_available(self):
        if self.txq.empty():
            self.phy.send_on_endpoint(self.tx_ep, b'\x00\x00\x00\x00\x00\x00\x00\x00')
        else:
            self.phy.send_on_endpoint(self.tx_ep, self.txq.get())

    def data_available(self, data):
        self.app.logger.info('[AudioStreaming] Got %#x bytes on streaming endpoint' % (len(data)))


class USBAudioStreamingInterface(USBInterface):

    def __init__(self, app, phy, iface_num, iface_alt, iface_str_idx, cs_ifaces, endpoints, device_class):
        super(USBAudioStreamingInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=iface_num,
            interface_alternate=iface_alt,
            interface_class=USBClass.Audio,
            interface_subclass=SUBCLASS_AUDIOSTREAMING,
            interface_protocol=0,
            interface_string_index=iface_str_idx,
            cs_interfaces=cs_ifaces,
            endpoints=endpoints,
            device_class=device_class
        )

    @mutable('audio_streaming_interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        return super(USBAudioStreamingInterface, self).get_descriptor(usb_type, valid)


class USBAudioControlInterface(USBInterface):

    def __init__(self, app, phy, iface_num, iface_alt, iface_str_idx, cs_ifaces, device_class):
        super(USBAudioControlInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=iface_num,
            interface_alternate=iface_alt,
            interface_class=USBClass.Audio,
            interface_subclass=SUBCLASS_AUDIOCONTROL,
            interface_protocol=0,
            interface_string_index=iface_str_idx,
            cs_interfaces=cs_ifaces,
            device_class=device_class
        )

    @mutable('audio_control_interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        return super(USBAudioControlInterface, self).get_descriptor(usb_type, valid)


class USBAudioDevice(USBDevice):

    name = 'AudioDevice'

    def __init__(self, app, phy, vid=0x0d8c, pid=0x000c, rev=0x0001, *args, **kwargs):
        audio_streaming = AudioStreaming(app, phy, 2, 1)
        device_class = USBAudioClass(app, phy)
        super(USBAudioDevice, self).__init__(
            app=app,
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=0x40,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='UMAP2 Sound Inc.',
            product_string='UMAP2 Audio Adapter',
            serial_number_string='UMAP2-12345-AUDIO',
            configurations=[
                USBConfiguration(
                    app=app, phy=phy, index=1,
                    string='UMAP2 Audio Configuration',
                    attributes=USBConfiguration.ATTR_BASE,
                    interfaces=[
                        # standard AC interface (4.3.1)
                        # At this point - with no endpoints
                        USBAudioControlInterface(
                            app=app, phy=phy, iface_num=0, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                # Class specific AC interface: header (4.3.2)
                                USBCSInterface('ACHeader', app, phy, '\x01\x00\x01\x64\x00\x02\x01\x02'),
                                # Class specific AC interface: input terminal (Table 4.3.2.1)
                                USBCSInterface('ACInputTerminal0', app, phy, '\x02\x01\x01\x01\x00\x02\x03\x00\x00\x00'),
                                USBCSInterface('ACInputTerminal1', app, phy, '\x02\x02\x01\x02\x00\x01\x01\x00\x00\x00'),
                                # Class specific AC interface: output terminal (Table 4.3.2.2)
                                USBCSInterface('ACOutputTerminal0', app, phy, '\x03\x06\x01\x03\x00\x09\x00'),
                                USBCSInterface('ACOutputTerminal1', app, phy, '\x03\x07\x01\x01\x00\x08\x00'),
                                # Class specific AC interface: selector unit (Table 4.3.2.4)
                                USBCSInterface('ACSelectorUnit', app, phy, '\x05\x08\x01\x0a\x00'),
                                # Class specific AC interface: feature unit (Table 4.3.2.5)
                                USBCSInterface('ACFeatureUnit0', app, phy, '\x06\x09\x0f\x01\x01\x02\x02\x00'),
                                USBCSInterface('ACFeatureUnit1', app, phy, '\x06\x0a\x02\x01\x43\x00\x00'),
                                USBCSInterface('ACFeatureUnit2', app, phy, '\x06\x0d\x02\x01\x03\x00\x00'),
                                # Class specific AC interface: mixer unit (Table 4.3.2.3)
                                USBCSInterface('ACMixerUnit', app, phy, '\x04\x0f\x02\x01\x0d\x02\x03\x00\x00\x00\x00'),
                            ],
                            device_class=device_class
                        ),
                        USBAudioStreamingInterface(
                            app=app, phy=phy, iface_num=1, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                USBCSInterface('ASGeneral', app, phy, '\x01\x01\x01\x01\x00'),
                                USBCSInterface('ASFormatType', app, phy, '\x02\x01\x02\x02\x10\x02\x44\xac\x00\x44\xac\x00'),
                            ],
                            endpoints=[
                                USBEndpoint(
                                    app=app, phy=phy, number=1,
                                    direction=USBEndpoint.direction_out,
                                    transfer_type=USBEndpoint.transfer_type_isochronous,
                                    sync_type=USBEndpoint.sync_type_adaptive,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=1,
                                    handler=audio_streaming.data_available,
                                    cs_endpoints=[
                                        USBCSEndpoint('ASEndpoint', app, phy, '\x01\x01\x01\x01\x00')
                                    ],
                                    device_class=device_class,
                                )
                            ],
                            device_class=device_class,
                        ),
                        USBAudioStreamingInterface(
                            app=app, phy=phy, iface_num=2, iface_alt=0, iface_str_idx=0,
                            cs_ifaces=[
                                USBCSInterface('ASGeneral', app, phy, '\x01\x07\x01\x01\x00'),
                                USBCSInterface('ASFormatType', app, phy, '\x02\x01\x01\x02\x10\x02\x44\xac\x00\x44\xac\x00'),
                            ],
                            endpoints=[
                                USBEndpoint(
                                    app=app, phy=phy, number=2,
                                    direction=USBEndpoint.direction_in,
                                    transfer_type=USBEndpoint.transfer_type_isochronous,
                                    sync_type=USBEndpoint.sync_type_async,
                                    usage_type=USBEndpoint.usage_type_data,
                                    max_packet_size=0x40,
                                    interval=1,
                                    handler=audio_streaming.buffer_available,
                                    cs_endpoints=[
                                        USBCSEndpoint('ASEndpoint', app, phy, '\x01\x01\x00\x00\x00')
                                    ],
                                    device_class=device_class,
                                )
                            ],
                            device_class=device_class,
                        )
                    ]
                ),
            ],
            device_vendor=None
        )


usb_device = USBAudioDevice
