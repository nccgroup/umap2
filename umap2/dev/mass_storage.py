'''
.. todo::

    Something to check all over the place - little/big endianess of data
    It is better now (6/6/2016) but still needs improvements
'''
from mmap import mmap
import os
import struct
from binascii import hexlify
from threading import Thread, Event
import time

from six.moves.queue import Queue
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_class import USBClass
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.helpers import mutable


class ScsiCmds(object):
    TEST_UNIT_READY = 0x00
    REQUEST_SENSE = 0x03
    READ_6 = 0x08
    WRITE_6 = 0x0A
    INQUIRY = 0x12
    MODE_SENSE_6 = 0x1A
    SEND_DIAGNOSTIC = 0x1D
    PREVENT_ALLOW_MEDIUM_REMOVAL = 0x1E
    READ_FORMAT_CAPACITIES = 0x23
    READ_CAPACITY_10 = 0x25
    READ_10 = 0x28
    WRITE_10 = 0x2A
    VERIFY_10 = 0x2F
    SYNCHRONIZE_CACHE = 0x35
    MODE_SENSE_10 = 0x5A


class ScsiSenseKeys(object):
    GOOD = 0x00
    RECOVERED_ERROR = 0x01
    NOT_READY = 0x02
    MEDIUM_ERROR = 0x03
    HARDWARE_ERROR = 0x04
    ILLEGAL_REQUEST = 0x05
    UNIT_ATTENTION = 0x06
    DATA_PROTECT = 0x07
    BLANK_CHECK = 0x08
    VENDOR_SPECIFIC = 0x09
    COPY_ABORTED = 0x0A
    ABORTED_COMMAND = 0x0B
    VOLUME_OVERFLOW = 0x0D
    MISCOMPARE = 0x0E


class USBMassStorageClass(USBClass):
    name = "USB mass storage class"

    def setup_local_handlers(self):
        self.local_handlers = {
            0xFF: self.handle_bulk_only_mass_storage_reset,
            0xFE: self.handle_get_max_lun,
        }

    @mutable('msc_bulk_only_mass_storage_reset_response')
    def handle_bulk_only_mass_storage_reset(self, req):
        return b''

    @mutable('msc_get_max_lun_response')
    def handle_get_max_lun(self, req):
        return b'\x00'


class DiskImage:
    def __init__(self, filename, block_size):
        self.filename = filename
        self.block_size = block_size

        statinfo = os.stat(self.filename)
        self.size = statinfo.st_size

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return int(self.size / self.block_size) - 1

    def get_sector_data(self, address):
        block_start = address * self.block_size
        block_end = (address + 1) * self.block_size   # slices are NON-inclusive

        return self.image[block_start:block_end]

    def put_sector_data(self, address, data):
        block_start = address * self.block_size
        block_end = (address + 1) * self.block_size   # slices are NON-inclusive

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()


def scsi_status(cbw, status):
    csw = b'USBS' + cbw.tag + struct.pack('<IB', 0x00000000, status)
    return csw


class ScsiDevice(USBBaseActor):
    '''
    Implementation of subset of the SCSI protocol
    '''
    name = 'SCSI stack'

    def __init__(self, app, disk_image):
        super(ScsiDevice, self).__init__(app)
        self.disk_image = disk_image
        self.handlers = {
            ScsiCmds.INQUIRY: self.handle_inquiry,
            ScsiCmds.REQUEST_SENSE: self.handle_request_sense,
            ScsiCmds.TEST_UNIT_READY: self.handle_test_unit_ready,
            ScsiCmds.READ_CAPACITY_10: self.handle_read_capacity_10,
            # ScsiCmds.SEND_DIAGNOSTIC: self.handle_send_diagnostic,
            ScsiCmds.PREVENT_ALLOW_MEDIUM_REMOVAL: self.handle_prevent_allow_medium_removal,
            ScsiCmds.WRITE_10: self.handle_write_10,
            ScsiCmds.READ_10: self.handle_read_10,
            # ScsiCmds.WRITE_6: self.handle_write_6,
            # ScsiCmds.READ_6: self.handle_read_6,
            # ScsiCmds.VERIFY_10: self.handle_verify_10,
            ScsiCmds.MODE_SENSE_6: self.handle_mode_sense_6,
            ScsiCmds.MODE_SENSE_10: self.handle_mode_sense_10,
            ScsiCmds.READ_FORMAT_CAPACITIES: self.handle_read_format_capacities,
            ScsiCmds.SYNCHRONIZE_CACHE: self.handle_synchronize_cache,
        }
        self.tx = Queue()
        self.rx = Queue()
        self.stop_event = Event()
        self.thread = Thread(target=self.handle_data_loop)
        self.thread.daemon = True
        self.thread.start()
        self.is_write_in_progress = False
        self.write_cbw = None
        self.write_base_lba = 0
        self.write_length = 0
        self.write_data = b''

    def stop(self):
        self.stop_event.set()

    def handle_data_loop(self):
        while not self.stop_event.isSet():
            if not self.rx.empty():
                data = self.rx.get()
                self.handle_data(data)
            else:
                time.sleep(0.0001)

    def handle_data(self, data):
        if self.is_write_in_progress:
            self.handle_write_data(data)
        else:
            cbw = CommandBlockWrapper(data)
            opcode = cbw.opcode
            if opcode in self.handlers:
                try:
                    resp = self.handlers[opcode](cbw)
                    if resp is not None:
                        self.tx.put(resp)
                    self.tx.put(scsi_status(cbw, 0))
                except Exception as ex:
                    self.warning('exception while proceeing opcode %#x' % (opcode))
                    self.warning(ex)
                    self.tx.put(scsi_status(cbw, 2))
            else:
                raise Exception('No handler for opcode %#x' % (opcode))

    def handle_write_data(self, data):
        self.debug("got %#x bytes of SCSI write data" % (len(data)))
        self.write_data += data
        if len(self.write_data) >= self.write_length:
            # done writing
            self.disk_image.put_sector_data(self.write_base_lba, self.write_data)
            self.is_write_in_progress = False
            self.write_data = b''
            self.tx.put(scsi_status(self.write_cbw, 0))

    @mutable('scsi_inquiry_response')
    def handle_inquiry(self, cbw):
        self.debug('SCSI Inquiry, data: %s' % hexlify(cbw.cb[1:]))
        peripheral = 0x00  # SBC
        RMB = 0x80  # Removable
        version = 0x00
        response_data_format = 0x01
        config = (0x00, 0x00, 0x00)
        vendor_id = b'PNY     '
        product_id = b'USB 2.0 FD      '
        product_revision_level = b'8.02'
        part1 = struct.pack('BBBB', peripheral, RMB, version, response_data_format)
        part2 = struct.pack('BBB', *config) + vendor_id + product_id + product_revision_level
        length = struct.pack('B', len(part2))
        response = part1 + length + part2
        return response

    @mutable('scsi_request_sense_response')
    def handle_request_sense(self, cbw):
        self.debug("SCSI Request Sense, data: %s" % hexlify(cbw.cb[1:]))
        response_code = 0x70
        valid = 0x00
        filemark = 0x06
        information = 0x00000000
        command_info = 0x00000000
        additional_sense_code = 0x3a
        additional_sens_code_qualifier = 0x00
        field_replacement_unti_code = 0x00
        sense_key_specific = b'\x00\x00\x00'

        part1 = struct.pack('<BBBI', response_code, valid, filemark, information)
        part2 = struct.pack(
            '<IBBB',
            command_info,
            additional_sense_code,
            additional_sens_code_qualifier,
            field_replacement_unti_code
        )
        part2 += sense_key_specific
        length = struct.pack('B', len(part2))
        response = part1 + length + part2
        return response

    @mutable('scsi_test_unit_ready_response')
    def handle_test_unit_ready(self, cbw):
        self.debug("SCSI Test Unit Ready, logical unit number: %02x" % (cbw.cb[1]))

    @mutable('scsi_read_capacity_10_response')
    def handle_read_capacity_10(self, cbw):
        self.debug("SCSI Read Capacity, data: %s" % hexlify(cbw.cb[1:]))
        lastlba = self.disk_image.get_sector_count()
        logical_block_address = struct.pack('>I', lastlba)
        length = 0x00000200
        response = logical_block_address + struct.pack('>I', length)
        return response

    @mutable('scsi_send_diagnostic_response')
    def handle_send_diagnostic(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_prevent_allow_medium_removal_response')
    def handle_prevent_allow_medium_removal(self, cbw):
        self.debug("SCSI Prevent/Allow Removal")

    @mutable('scsi_write_10_response')
    def handle_write_10(self, cbw):
        self.debug("SCSI Write (10), data: %s" % hexlify(cbw.cb[1:]))

        base_lba = struct.unpack('>I', cbw.cb[2:6])[0]
        num_blocks = struct.unpack('>H', cbw.cb[7:9])[0]

        self.debug("SCSI Write (10), lba %#x + %#x block(s)" % (base_lba, num_blocks))

        # save for later
        self.write_cbw = cbw
        self.write_base_lba = base_lba
        self.write_length = num_blocks * self.disk_image.block_size
        self.is_write_in_progress = True

    def handle_read_10(self, cbw):
        base_lba = struct.unpack('>I', cbw.cb[2:6])[0]
        num_blocks = struct.unpack('>H', cbw.cb[7:9])[0]
        self.debug("SCSI Read (10), lba %#x + %#x block(s)" % (base_lba, num_blocks))
        for block_num in range(num_blocks):
            data = self.disk_image.get_sector_data(base_lba + block_num)
            self.tx.put(data)

    @mutable('scsi_write_6_response')
    def handle_write_6(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_read_6_response')
    def handle_read_6(self, cbw):
        raise NotImplementedError('yet...')

    @mutable('scsi_verify_10_response')
    def handle_verify_10(self, cbw):
        raise NotImplementedError('yet...')

    def handle_scsi_mode_sense(self, cbw):
        page = cbw.cb[2] & 0x3f

        self.debug("SCSI Mode Sense, page code 0x%02x" % page)

        if page == 0x1c:
            medium_type = 0x00
            device_specific_param = 0x00
            block_descriptor_len = 0x00
            mode_page_1c = b'\x1c\x06\x00\x05\x00\x00\x00\x00'
            body = struct.pack('BBB', medium_type, device_specific_param, block_descriptor_len)
            body += mode_page_1c
            length = struct.pack('<B', len(body))
            response = length + body

        elif page == 0x3f:
            length = 0x45  # .. todo:: this seems awefully wrong
            medium_type = 0x00
            device_specific_param = 0x00
            block_descriptor_len = 0x08
            mode_page = 0x00000000
            response = struct.pack('<BBBBI', length, medium_type, device_specific_param, block_descriptor_len, mode_page)
        else:
            length = 0x07
            medium_type = 0x00
            device_specific_param = 0x00
            block_descriptor_len = 0x00
            mode_page = 0x00000000
            response = struct.pack('<BBBBI', length, medium_type, device_specific_param, block_descriptor_len, mode_page)
        return response

    @mutable('scsi_mode_sense_6_response')
    def handle_mode_sense_6(self, cbw):
        return self.handle_scsi_mode_sense(cbw)

    @mutable('scsi_mode_sense_10_response')
    def handle_mode_sense_10(self, cbw):
        return self.handle_scsi_mode_sense(cbw)

    @mutable('scsi_read_format_capacities')
    def handle_read_format_capacities(self, cbw):
        self.debug("SCSI Read Format Capacity")
        # header
        response = struct.pack('>I', 8)
        num_sectors = 0x1000
        reserved = 0x1000
        sector_size = 0x200
        response += struct.pack('>IHH', num_sectors, reserved, sector_size)
        return response

    @mutable('scsi_synchronize_cache_response')
    def handle_synchronize_cache(self, cbw):
        self.debug("Synchronize Cache (10)")


class CommandBlockWrapper:
    def __init__(self, bytestring):
        as_array = bytearray(bytestring)
        self.signature = bytestring[0:4]
        self.tag = bytestring[4:8]
        self.data_transfer_length = struct.unpack('<I', as_array[8:12])[0]
        self.flags = as_array[12]
        self.lun = as_array[13] & 0x0f
        self.cb_length = as_array[14] & 0x1f
        # self.cb = bytestring[15:15+self.cb_length]
        self.cb = as_array[15:]
        self.opcode = self.cb[0]

    def __str__(self):
        s = "sig: %s\n" % hexlify(self.signature)
        s += "tag: %s\n" % hexlify(self.tag)
        s += "data transfer len: %s\n" % self.data_transfer_length
        s += "flags: %s\n" % self.flags
        s += "lun: %s\n" % self.lun
        s += "command block len: %s\n" % self.cb_length
        s += "command block: %s\n" % hexlify(self.cb)
        return s


class USBMassStorageInterface(USBInterface):
    '''
    .. todo:: all handlers - should be more dynamic??
    '''
    name = "USB mass storage interface"

    def __init__(self, app, scsi_device, usbclass, sub, proto):
        # TODO: un-hardcode string index
        super(USBMassStorageInterface, self).__init__(
            app=app,
            interface_number=0,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=[
                USBEndpoint(
                    app=app,
                    number=1,
                    direction=USBEndpoint.direction_out,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_data_available
                ),
                USBEndpoint(
                    app=app,
                    number=3,
                    direction=USBEndpoint.direction_in,
                    transfer_type=USBEndpoint.transfer_type_bulk,
                    sync_type=USBEndpoint.sync_type_none,
                    usage_type=USBEndpoint.usage_type_data,
                    max_packet_size=0x40,
                    interval=0,
                    handler=self.handle_buffer_available
                ),
                # USBEndpoint(
                #     app=app,
                #     number=2,
                #     direction=USBEndpoint.direction_in,
                #     transfer_type=USBEndpoint.transfer_type_interrupt,
                #     sync_type=USBEndpoint.sync_type_none,
                #     usage_type=USBEndpoint.usage_type_data,
                #     max_packet_size=0x40,
                #     interval=0,
                #     handler=None
                # ),
            ],
            device_class=USBMassStorageClass(app),
        )
        self.scsi_device = scsi_device

    def handle_buffer_available(self):
        if not self.scsi_device.tx.empty():
            data = self.scsi_device.tx.get()
            self.app.send_on_endpoint(3, data)

    def handle_data_available(self, data):
        self.debug("handling %d bytes of SCSI data" % (len(data)))
        self.supported()
        self.scsi_device.rx.put(data)


class USBMassStorageDevice(USBDevice):
    name = "USB mass storage device"

    def __init__(
        self, app, vid=0x154b, pid=0x6545, rev=0x0002,
        usbclass=USBClass.MassStorage, subclass=0x06, proto=0x50,
        disk_image_filename='stick.img'
    ):
        self.disk_image = DiskImage(disk_image_filename, 0x200)
        self.scsi_device = ScsiDevice(app, DiskImage(disk_image_filename, 0x200))

        super(USBMassStorageDevice, self).__init__(
            app=app,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string="PNY",
            product_string="USB 2.0 FD",
            serial_number_string="4731020ef1914da9",
            configurations=[
                USBConfiguration(
                    app=app,
                    index=1,
                    string="MassStorage config",
                    interfaces=[
                        USBMassStorageInterface(app, self.scsi_device, usbclass, subclass, proto)
                    ]
                )
            ],
        )

    def disconnect(self):
        super(USBMassStorageDevice, self).disconnect()
        self.scsi_device.stop()
        self.disk_image.close()


usb_device = USBMassStorageDevice
