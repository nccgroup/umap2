# MAXUSBApp.py
#
# Contains class definition for MAXUSBApp.

import os
import struct
import time
from binascii import hexlify
from umap2.phy.facedancer.facedancer import FacedancerApp, FacedancerCommand


class MAXUSBApp(FacedancerApp):
    app_name = "MAXUSB"
    app_num = 0x40

    reg_ep0_fifo = 0x00
    reg_ep1_out_fifo = 0x01
    reg_ep2_in_fifo = 0x02
    reg_ep3_in_fifo = 0x03
    reg_setup_data_fifo = 0x04
    reg_ep0_byte_count = 0x05
    reg_ep1_out_byte_count = 0x06
    reg_ep2_in_byte_count = 0x07
    reg_ep3_in_byte_count = 0x08
    reg_ep_stalls = 0x09
    reg_clr_togs = 0x0a
    reg_endpoint_irq = 0x0b
    reg_endpoint_interrupt_enable = 0x0c
    reg_usb_irq = 0x0d
    reg_usb_interrupt_enable = 0x0e
    reg_usb_control = 0x0f
    reg_cpu_control = 0x10
    reg_pin_control = 0x11
    reg_revision = 0x12
    reg_function_address = 0x13
    reg_io_pins = 0x14

    # bitmask values for reg_endpoint_irq = 0x0b
    is_setup_data_avail = 0x20     # SUDAVIRQ
    is_in3_buffer_avail = 0x10     # IN3BAVIRQ
    is_in2_buffer_avail = 0x08     # IN2BAVIRQ
    is_out1_data_avail = 0x04     # OUT1DAVIRQ
    is_out0_data_avail = 0x02     # OUT0DAVIRQ
    is_in0_buffer_avail = 0x01     # IN0BAVIRQ

    # bitmask values for reg_usb_control = 0x0f
    usb_control_vbgate = 0x40
    usb_control_connect = 0x08

    # bitmask values for reg_pin_control = 0x11
    interrupt_level = 0x08
    full_duplex = 0x10

    def __init__(self, device, app, fuzzer=None):
        super(MAXUSBApp, self).__init__(device)

        self.connected_device = None
        self.fuzzer = fuzzer
        self.reply_buffer = ""
        self.stop = False
        self.retries = False
        self.enable()

        self.app = app

        rev = self.read_register(self.reg_revision)
        self.info('revision: %d' % rev)

        # set duplex and negative INT level (from GoodFEDMAXUSB.py)
        self.write_register(self.reg_pin_control, self.full_duplex | self.interrupt_level)

    def get_mutation(self, stage, data=None):
        if self.fuzzer:
            data = {} if data is None else data
            return self.fuzzer.get_mutation(stage=stage, data=data)
        return None

    def init_commands(self):
        self.read_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.write_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.enable_app_cmd = FacedancerCommand(self.app_num, 0x10, b'')
        self.ack_cmd = FacedancerCommand(self.app_num, 0x00, b'\x01')

    def read_register(self, reg_num, ack=False):
        self.verbose("reading register 0x%02x" % reg_num)
        mask = 0 if not ack else 1
        self.read_register_cmd.data = struct.pack('<BB', (reg_num << 3) | mask, 0)
        self.device.writecmd(self.read_register_cmd)
        resp = self.device.readcmd()
        reg_val = struct.unpack('<B', resp.data[1:2])[0]
        self.verbose("read register 0x%02x has value 0x%02x" % (reg_num, reg_val))
        return reg_val

    def write_register(self, reg_num, value, ack=False):
        self.verbose("writing register 0x%02x with value 0x%02x" % (reg_num, value))
        mask = 2 if not ack else 3
        self.write_register_cmd.data = struct.pack('<BB', (reg_num << 3) | mask, value)
        self.device.writecmd(self.write_register_cmd)
        self.device.readcmd()

    def get_version(self):
        return self.read_register(self.reg_revision)

    def ack_status_stage(self):
        self.verbose("sending ack!")
        self.device.writecmd(self.ack_cmd)
        self.device.readcmd()

    def connect(self, usb_device):
        self.write_register(self.reg_usb_control, self.usb_control_vbgate | self.usb_control_connect)
        self.connected_device = usb_device
        self.info("connected device %s" % self.connected_device.name)

    def disconnect(self):
        self.write_register(self.reg_usb_control, self.usb_control_vbgate)
        if self.connected_device:
            self.info("disconnected device %s" % self.connected_device.name)
        else:
            self.error('disconnect called when already disconnected')
        self.connected_device = None

    def is_connected(self):
        return self.connected_device is not None

    def clear_irq_bit(self, reg, bit):
        self.write_register(reg, bit)

    def read_bytes(self, reg, n):
        self.verbose("reading %d bytes from register %s" % (n, reg))
        data = struct.pack('B', reg << 3) + b'\00' * n
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()
        self.verbose("read %d bytes from register %d" % (len(resp.data) - 1, reg))
        return resp.data[1:]

    def write_bytes(self, reg, data):
        data = struct.pack('<B', (reg << 3) | 3) + data
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        self.device.readcmd()  # null response

        self.verbose("wrote %d bytes to register %d" % (len(data) - 1, reg))

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def send_on_endpoint(self, ep_num, data):
        if ep_num == 0:
            fifo_reg = self.reg_ep0_fifo
            bc_reg = self.reg_ep0_byte_count
        elif ep_num == 2:
            fifo_reg = self.reg_ep2_in_fifo
            bc_reg = self.reg_ep2_in_byte_count
        elif ep_num == 3:
            fifo_reg = self.reg_ep3_in_fifo
            bc_reg = self.reg_ep3_in_byte_count
        else:
            raise ValueError('endpoint ' + str(ep_num) + ' not supported')

        # FIFO buffer is only 64 bytes, must loop
        while len(data) > 64:
            self.write_bytes(fifo_reg, data[:64])
            self.write_register(bc_reg, 64, ack=True)

            data = data[64:]

        self.write_bytes(fifo_reg, data)
        self.write_register(bc_reg, len(data), ack=True)

        self.verbose("wrote %s to endpoint %#x" % (hexlify(data), ep_num))

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def read_from_endpoint(self, ep_num):
        if ep_num != 1:
            return b''
        byte_count = self.read_register(self.reg_ep1_out_byte_count)
        if byte_count == 0:
            return b''
        data = self.read_bytes(self.reg_ep1_out_fifo, byte_count)
        self.verbose("read %s from endpoint %#x" % (hexlify(data), ep_num))
        return data

    def stall_ep0(self):
        self.verbose("stalling endpoint 0")
        self.write_register(self.reg_ep_stalls, 0x23)

    def check_connection_commands(self):
        '''
        :return: whether performed reconnection
        '''
        dev = self.connected_device
        if self.should_disconnect():
            self.disconnect()
            self.clear_disconnect_trigger()
            # wait for reconnection request; no point in returning to service_irqs loop while not connected!
            while not self.should_reconnect():
                self.clear_disconnect_trigger()  # be robust to additional disconnect requests
                time.sleep(0.1)
            # now that we received a reconnect request, flow into the handling of it...
        # be robust to reconnection requests, whether received after a disconnect request, or standalone
        # (not sure this is right, might be better to *not* be robust in the face of possible misuse?)
        if self.should_reconnect():
            self.connect(dev)
            self.clear_reconnect_trigger()
            return True
        return False

    def should_reconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/umap_kitty/trigger_reconnect'):
                return True
        return False

    def clear_reconnect_trigger(self):
        trigger = '/tmp/umap_kitty/trigger_reconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def should_disconnect(self):
        if self.fuzzer:
            if os.path.isfile('/tmp/umap_kitty/trigger_disconnect'):
                return True
        return False

    def clear_disconnect_trigger(self):
        trigger = '/tmp/umap_kitty/trigger_disconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def send_heartbeat(self):
        heartbeat_file = '/tmp/umap_kitty/heartbeat'
        if os.path.isdir(os.path.dirname(heartbeat_file)):
            with open(heartbeat_file, 'a'):
                os.utime(heartbeat_file, None)

    def service_irqs(self):
        count = 0
        tmp_irq = 0

        while not self.stop:
            irq = self.read_register(self.reg_endpoint_irq)

            if irq == tmp_irq:
                count += 1
            else:
                self.send_heartbeat()
                count = 0

            self.verbose("read endpoint irq: 0x%02x" % irq)

            if irq & ~ (
                self.is_in0_buffer_avail |
                self.is_in2_buffer_avail |
                self.is_in3_buffer_avail
            ):
                self.debug("notable irq: 0x%02x" % irq)

            if irq & self.is_setup_data_avail:
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_setup_data_avail)

                b = self.read_bytes(self.reg_setup_data_fifo, 8)
                self.connected_device.handle_request(b)

            if irq & self.is_out1_data_avail:
                data = self.read_from_endpoint(1)
                if data:
                    self.connected_device.handle_data_available(1, data)
                self.clear_irq_bit(self.reg_endpoint_irq, self.is_out1_data_avail)

            if irq & self.is_in2_buffer_avail:
                try:
                    self.connected_device.handle_buffer_available(2)
                except:
                    self.error('umap ignored the exception for some reason... will need to address that later on')
                    raise

            if irq & self.is_in3_buffer_avail:
                try:
                    self.connected_device.handle_buffer_available(3)
                except:
                    self.error('umap ignored the exception for some reason... will need to address that later on')
                    raise
            tmp_irq = irq
            if self.app.packet_processed():
                break

    # code that should be removed soon
    def usb_function_supported(self):
        self.app.usb_function_supported()
