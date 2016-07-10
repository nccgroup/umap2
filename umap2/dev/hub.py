'''
Contains class definitions to implement a USB hub.
'''
import struct
from umap2.core.usb import DescriptorType
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.fuzz.helpers import mutable


class USBHubClass(USBClass):
    name = 'HubClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x00: self.handle_get_hub_status,
            0x03: self.handle_set_port_feature,
        }

    @mutable('hub_get_hub_status_response')
    def handle_get_hub_status(self, req):
        i = req.index
        if i:
            self.info('GetPortStatus (%d)' % i)
        else:
            self.info('GetHubStatus')
        return b'\x00\x00\x00\x00'

    @mutable('hub_set_port_feature_response')
    def handle_set_port_feature(self, req):
        return b'\x01'


class USBHubInterface(USBInterface):
    name = 'HubInterface'

    def __init__(self, app, phy, num=0):
        # TODO: un-hardcode string index
        super(USBHubInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=num,
            interface_alternate=0,
            interface_class=USBClass.Hub,
            interface_subclass=0,
            interface_protocol=0,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    app=app,
                    phy=phy,
                    number=0x2,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_interrupt,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0x40,
                    handler=self.handle_buffer_available
                )
            ],
            descriptors={
                DescriptorType.hub: self.get_hub_descriptor
            },
            device_class=USBHubClass(app, phy)
        )

    @mutable('hub_descriptor')
    def get_hub_descriptor(self, **kwargs):
        bLength = 9
        bDescriptorType = 0x29
        bNbrPorts = 4
        wHubCharacteristics = 0xe000
        bPwrOn2PwrGood = 0x32
        bHubContrCurrent = 0x64
        DeviceRemovable = 0
        PortPwrCtrlMask = 0xff

        return struct.pack(
            '<BBBHBBBB',
            bLength,
            bDescriptorType,
            bNbrPorts,
            wHubCharacteristics,
            bPwrOn2PwrGood,
            bHubContrCurrent,
            DeviceRemovable,
            PortPwrCtrlMask
        )

    def handle_buffer_available(self):
        return


class USBHubDevice(USBDevice):
    name = 'HubDevice'

    def __init__(self, app, phy, vid=0x05e3, pid=0x0610, rev=0x7732, **kwargs):
        super(USBHubDevice, self).__init__(
            app=app,
            phy=phy,
            device_class=USBClass.Hub,
            device_subclass=0,
            protocol_rel_num=1,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Genesys Logic, Inc',
            product_string='USB2.0 Hub',
            serial_number_string='1234',
            configurations=[
                USBConfiguration(
                    app=app,
                    phy=phy,
                    index=1,
                    string='Emulated Hub',
                    interfaces=[
                        USBHubInterface(app, phy)
                    ],
                    attributes=USBConfiguration.ATTR_SELF_POWERED,
                )
            ],
        )


usb_device = USBHubDevice
