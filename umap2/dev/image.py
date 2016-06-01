# USBImage.py
#
# Contains class definitions to implement a USB image device.
'''
.. todo::

    Still doesn't really work, not sure why.
    Should look deeper into the implementation and spec.
'''
import struct
from binascii import hexlify
from mmap import mmap
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_class import USBClass
from umap2.fuzz.wrappers import mutable


class USBImageClass(USBClass):
    name = "USB image class"

    def setup_local_handlers(self):
        self.local_handlers = {
            0x66: self.handle_device_reset,
        }

    @mutable('image_device_reset_response')
    def handle_device_reset(self, req):
        return b''


class Opcodes(object):
    GetDeviceInfo = 0x1001
    OpenSession = 0x1002
    CloseSession = 0x1003
    GetStorageIDs = 0x1004
    GetStorageInfo = 0x1005
    GetNumObjects = 0x1006
    GetObjectHandles = 0x1007
    GetObjectInfo = 0x1008
    GetObject = 0x1009
    GetThumb = 0x100a
    SendObjectInfo = 0x100c
    SendObject = 0x100d
    GetDevicePropDesc = 0x1014
    GetDevicePropValue = 0x1015
    SetDevicePropValue = 0x1016
    GetPartialObject = 0x101b


class Events(object):
    StoredAdded = 0x4004
    StoreRemoved = 0x4005
    DeviceInfoChanged = 0x4008
    RequestObjectTransfer = 0x4009


def encode_string(st):
    st += '\x00'
    est = ''.join(x + '\x00' for x in st)
    length = len(st)
    return str.encode(chr(length) + est)


class USBImageInterface(USBInterface):
    name = "USB image interface"

    def __init__(self, int_num, app, thumb_image, partial_image, usbclass, sub, proto):
        self.thumb_image = thumb_image
        self.partial_image = partial_image
        self.operations = {
            Opcodes.GetDeviceInfo: (self.op_GetDeviceInfo_1, self.op_GetDeviceInfo_2),
            Opcodes.OpenSession: (self.op_OpenSession_1, self.op_OpenSession_2),
            Opcodes.CloseSession: (self.op_CloseSession_1, self.op_CloseSession_2),
            Opcodes.GetStorageIDs: (self.op_GetStorageIDs_1, self.op_GetStorageIDs_2),
            Opcodes.GetStorageInfo: (self.op_GetStorageInfo_1, self.op_GetStorageInfo_2),
            # Opcodes.GetNumObjects: (self.op_GetNumObjects_1, self.op_GetNumObjects_2),
            Opcodes.GetObjectHandles: (self.op_GetObjectHandles_1, self.op_GetObjectHandles_2),
            Opcodes.GetObjectInfo: (self.op_GetObjectInfo_1, self.op_GetObjectInfo_2),
            # Opcodes.GetObject: (self.op_GetObject_1, self.op_GetObject_2),
            Opcodes.GetThumb: (self.op_GetThumb_1, self.op_GetThumb_2),
            # Opcodes.SendObjectInfo: (self.op_SendObjectInfo_1, self.op_SendObjectInfo_2),
            # Opcodes.SendObject: (self.op_SendObject_1, self.op_SendObject_2),
            # Opcodes.GetDevicePropDesc: (self.op_GetDevicePropDesc_1, self.op_GetDevicePropDesc_2),
            # Opcodes.GetDevicePropValue: (self.op_GetDevicePropValue_1, self.op_GetDevicePropValue_2),
            Opcodes.SetDevicePropValue: (self.op_SetDevicePropValue_1, self.op_SetDevicePropValue_2),
            # Opcodes.GetPartialObject: (self.op_GetPartialObject_1, self.op_GetPartialObject_2),
        }
        descriptors = {}

        endpoints = [
            USBEndpoint(
                app=app,
                number=1,
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
                number=0x2,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0,
                handler=self.handle_ep2_buffer_available
            ),
            USBEndpoint(
                app=app,
                number=0x3,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_interrupt,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0x10,
                handler=self.handle_ep3_buffer_available
            )
        ]

        # TODO: un-hardcode string index (last arg before "verbose")
        super(USBImageInterface, self).__init__(
            app=app,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=endpoints,
            descriptors=descriptors
        )

        self.device_class = USBImageClass(app)
        self.device_class.set_interface(self)

    def create_send_ok(self, transaction_id):
        self.debug(self.name, "sent Image:OK")
        container_type = 0x03  # Response block
        response_code = 0x2001  # "OK"
        container_length = 0x0000000c  # always this length
        response = struct.pack('<BHII', container_length, container_type, response_code, transaction_id)
        return response

    def handle_ep2_buffer_available(self):
        self.verbose('ep2 - buffer available')

    def handle_ep3_buffer_available(self):
        self.verbose('ep3 - buffer available')

    def handle_ep1_data_available(self, data):
        self.info('Request: %s' % hexlify(data))
        self.device_class.supported()
        container = ContainerRequestWrapper(data)
        opcode = container.opcode
        response = None
        response2 = None

        if opcode in self.operations:
            op1, op2 = self.operations[opcode]
            fuzzing_data = {
                'opcode': struct.pack('<H', container.opcode),
                'transaction_id': struct.pack('<I', container.transaction_id),
                'parameter1': struct.pack('<I', container.parameter1),
            }
            if op1:
                response = op1(container, fuzzing_data=fuzzing_data)
            if op2:
                response2 = op2(container, fuzzing_data=fuzzing_data)

        if response:
            self.info('Response: %s' % hexlify(response))
            self.verbose("responding with %d bytes: %s" % (len(response), hexlify(response)))
            self.configuration.device.app.send_on_endpoint(2, response)

        if response2:
            self.info('Response2: %s' % hexlify(response2))
            self.verbose("responding with %d bytes: %s" % (len(response), hexlify(response)))
            self.configuration.device.app.send_on_endpoint(2, response2)

    @mutable('image_OpenSession_response1')
    def op_OpenSession_1(self, container, **kwargs):
        return None

    @mutable('image_OpenSession_response2')
    def op_OpenSession_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_CloseSession_response1')
    def op_CloseSession_1(self, container, **kwargs):
        return None

    @mutable('image_CloseSession_response2')
    def op_CloseSession_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_SetDevicePropValue_response1')
    def op_SetDevicePropValue_1(self, container, **kwargs):
        return None

    @mutable('image_SetDevicePropValue_response2')
    def op_SetDevicePropValue_2(self, container, **kwargs):
        response = None
        if container.container_type == 2:  # Data block
            response = self.create_send_ok(container.transaction_id)
        return response

    @mutable('image_GetStorageInfo_response1')
    def op_GetStorageInfo_1(self, container, **kwargs):
        container.container_type = 0x0002  # Data block
        operation_code = 0x1005  # GetStorageInfo
        storage_type = 0x0004  # Removable RAM
        filesystem_type = 0x0003  # DCF (Design rule for Camera File system)
        access_capability = 0x0000  # Read-write
        max_capacity = 0x0000000078180000  # 2014838784 bytes
        free_space_in_bytes = 0x0000000077da8000  # 2010808320 bytes
        free_space_in_images = 0x00000000  # 0 bytes
        storage_description = 0x00
        volume_label = 0x00

        response = struct.pack(
            '<HHIHHHQQIBB',
            container.container_type,
            operation_code,
            container.transaction_id,
            storage_type,
            filesystem_type,
            access_capability,
            max_capacity,
            free_space_in_bytes,
            free_space_in_images,
            storage_description,
            volume_label
        )

        container_length = len(response) + 4
        container_length_bytes = struct.pack('<I', container_length)

        response = container_length_bytes + response
        return response

    @mutable('image_GetStorageInfo_response2')
    def op_GetStorageInfo_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_GetObjectInfo_response1')
    def op_GetObjectInfo_1(self, container, **kwargs):
        container_type = 0x0002  # Data block
        operation_code = 0x1008  # GetObjectInfo
        storage_id = 0x00010001  # Phy: 0x0001 Log: 0x0001
        object_format = 0x3801  # EXIF/JPEG
        protection_status = 0x0000  # no protection
        object_compressed_size = 0x0031d658  # 3266136
        thumb_format = 0x3808  # JFIF
        thumb_compressed_size = 0x00000dcd  # 3533
        thumb_pixel_width = 0x000000a0  # 160
        thumb_pixel_height = 0x00000078  # 120
        image_pixel_width = 0x00000e40  # 3648
        image_pixel_height = 0x00000ab0  # 2736
        image_pixel_depth = 0x00000018  # 24
        parent_object = 0x00000000  # Object handle = 0
        association_type = 0x0000  # undefined
        association_desc = 0x00000000  # undefined
        sequence_number = 0x00000000  # 0
        # these fields stay as the are ...
        filename = encode_string('P1010749.JPG')
        capture_date = encode_string('20130723T110506')
        modification_date = encode_string('20130723T110506')
        keywords = b'\x00'  # none

        response = struct.pack(
            '<HHIHHIHIIIIIIIHII',
            container_type,
            operation_code,
            storage_id,
            object_format,
            protection_status,
            object_compressed_size,
            thumb_format,
            thumb_compressed_size,
            thumb_pixel_width,
            thumb_pixel_height,
            image_pixel_width,
            image_pixel_height,
            image_pixel_depth,
            parent_object,
            association_type,
            association_desc,
            sequence_number,
        )
        response += filename + capture_date + modification_date + keywords
        container_length = len(response) + 4
        response = struct.pack('<I', container_length) + response
        return response

    @mutable('image_GetObjectInfo_response2')
    def op_GetObjectInfo_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_GetObjectHandles_response1')
    def op_GetObjectHandles_1(self, container, **kwargs):
        container_type = 0x0002  # Data block
        operation_code = Opcodes.GetObjectHandles
        object_handle_array_size = 0x00000001  # 1 array size
        object_handle = 0x421942ca  # Object handle
        response = struct.pack(
            '<HHIII',
            container_type,
            operation_code,
            container.transaction_id,
            object_handle_array_size,
            object_handle,
        )
        container_length = len(response) + 4
        response = struct.pack('<I', container_length) + response
        return response

    @mutable('image_GetObjectHandles_response2')
    def op_GetObjectHandles_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_GetStorageIDs_response1')
    def op_GetStorageIDs_1(self, container, **kwargs):
        container_type = 0x0002  # Data block
        operation_code = Opcodes.GetStorageIDs
        storage_id_array_size = 0x00000001  # 1 storage ID
        storage_id = 0x00010001  # Phys: 0x0001 Log: 0x0001
        response = struct.pack(
            '<HHIII',
            container_type,
            operation_code,
            container.transaction_id,
            storage_id_array_size,
            storage_id,
        )
        container_length = len(response) + 4
        response = struct.pack('<I', container_length) + response
        return response

    @mutable('image_GetStorageIDs_response2')
    def op_GetStorageIDs_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_GetDeviceInfo_response1')
    def op_GetDeviceInfo_1(self, container, **kwargs):
        container_type = 0x0002  # Data block
        operation_code = Opcodes.GetDeviceInfo
        standard_version = 0x0064  # version 1.0
        vendor_extension_id = 0x00000006  # Microsoft Corporation
        vendor_extension_version = 0x0064  # version 1.0
        vendor_extension_desc = 0x00
        functional_mode = 0x0000  # standard mode
        operations_supported_array = [o for o in Opcodes]  # 2 bytes each
        events_supported_array = [e for e in Events]  # 2 bytes each
        device_properties_supported_array = [
            0xd406,  # Unknown property
            0xd407,  # Unknown property
        ]
        capture_formats_supported_array = []
        image_formats_supported_array = [
            0x3001,  # Association (Folder)
            0x3002,  # Script
            0x3006,  # DPOF
            0x300d,  # Unknown image format
            0x3801,  # EXIF/JPEG
            0x380d,  # TIFF
        ]

        manufacturer = encode_string('Panasonic')
        model = encode_string('DMC-FS7')
        device_version = encode_string('1.0')
        serial_number = encode_string('0000000000000000001X0209030754')

        response = struct.pack(
            '<HHIHIHBH',
            container_type,
            operation_code,
            container.transaction_id,
            standard_version,
            vendor_extension_id,
            vendor_extension_version,
            vendor_extension_desc,
            functional_mode,
        )

        def pack_array(arr):
            resp = struct.pack('<I', len(arr))
            for elem in arr:
                resp += struct.pack('<H', elem)
            return resp

        response += pack_array(operations_supported_array)
        response += pack_array(events_supported_array)
        response += pack_array(device_properties_supported_array)
        response += pack_array(capture_formats_supported_array)
        response += pack_array(image_formats_supported_array)
        response = manufacturer + model + device_version + serial_number

        container_length = len(response) + 4
        response = struct.pack('<I', container_length) + response
        return response

    @mutable('image_GetDeviceInfo_response2')
    def op_GetDeviceInfo_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)

    @mutable('image_GetThumb_response1')
    def op_GetThumb_1(self, container, **kwargs):
        thumb_data = (self.thumb_image.read_data())
        container_type = 0x0002  # Data block
        operation_code = Opcodes.GetThumb
        response = struct.pack('<HHI', container_type, operation_code, container.transaction_id)
        thumbnail_data_object = thumb_data
        x = 0
        while x < len(thumbnail_data_object):
            response += struct.pack('<B', thumbnail_data_object[x])
            x += 1
        container_length = len(response) + 4
        response = struct.pack('<I', container_length) + response
        return response

    @mutable('image_GetThumb_response2')
    def op_GetThumb_2(self, container, **kwargs):
        return self.create_send_ok(container.transaction_id)


class ThumbImage:
    def __init__(self, filename):
        self.filename = filename

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def read_data(self):
        return self.image


class ContainerRequestWrapper:
    def __init__(self, bytestring):
        (
            self.container_length,
            self.container_type,
            self.opcode,
            self.transaction_id,
            self.parameter1
        ) = struct.unpack('<IHHII', bytestring[:16])


class USBImageDevice(USBDevice):
    name = "USB image device"

    def __init__(
        self, app, vid=0x04da, pid=0x2374, rev=0x1000,
        thumb_image_filename='ncc_group_logo.jpg',
        usbclass=USBClass.Image, subclass=0, proto=0
    ):
        self.thumb_image = ThumbImage(thumb_image_filename)
        self.partial_image = ThumbImage("ncc_group_logo.bin")

        interface = USBImageInterface(0, app, self.thumb_image, self.partial_image, usbclass, subclass, proto)

        config = USBConfiguration(
            app=app,
            configuration_index=1,
            configuration_string="Image",
            interfaces=[interface]
        )

        super(USBImageDevice, self).__init__(
            app=app,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=0x40,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string="Panasonic",
            product_string="DMC-FS7",
            serial_number_string="0000000000000000001X0209030754",
            configurations=[config],
        )

    def disconnect(self):
        self.thumb_image.close()
        self.partial_image.close()
        USBDevice.disconnect(self)


usb_device = USBImageDevice
