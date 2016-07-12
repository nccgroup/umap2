'''
Facedancer (with MAX342x chip) USB physical interface

This code is based on the MAXUSBApp and FacedancerApp implementation
in GootFET by Travis Goodspeed: https://github.com/travisgoodspeed/goodfet
'''
import struct
from binascii import hexlify
from umap2.phy.iphy import PhyInterface
from umap2.phy.facedancer.facedancer import FacedancerCommand, Facedancer


class Regs:
    '''
    Enumeration of MAX342x registers
    '''
    ep0_fifo = 0x00
    ep1_out_fifo = 0x01
    ep2_in_fifo = 0x02
    ep3_in_fifo = 0x03
    setup_data_fifo = 0x04
    ep0_byte_count = 0x05
    ep1_out_byte_count = 0x06
    ep2_in_byte_count = 0x07
    ep3_in_byte_count = 0x08
    ep_stalls = 0x09
    clr_togs = 0x0a
    endpoint_irq = 0x0b
    endpoint_interrupt_enable = 0x0c
    usb_irq = 0x0d
    usb_interrupt_enable = 0x0e
    usb_control = 0x0f
    cpu_control = 0x10
    pin_control = 0x11
    revision = 0x12
    function_address = 0x13
    io_pins = 0x14


class Max342xPhy(PhyInterface):
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

    def __init__(self, app, serial_port):
        super(Max342xPhy, self).__init__(app, 'Max342xPhy')
        self.app_num = 0x40
        self.device = Facedancer(serial_port)
        self.init_commands()
        self.info('Initialized commands')
        self.reply_buffer = ''
        self.retries = False
        self.enable()
        rev = self.read_register(Regs.revision)
        self.info('Facedancer revision: %s' % rev)
        self.write_register(Regs.pin_control, self.full_duplex | self.interrupt_level)

    def enable(self):
        for i in range(3):
            self.device.writecmd(self.enable_app_cmd)
            self.device.readcmd()
        self.info('Enabled')

    def init_commands(self):
        self.read_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.write_register_cmd = FacedancerCommand(self.app_num, 0x00, b'')
        self.enable_app_cmd = FacedancerCommand(self.app_num, 0x10, b'')
        self.ack_cmd = FacedancerCommand(self.app_num, 0x00, b'\x01')

    def read_register(self, reg_num, ack=False):
        self.verbose('Reading register 0x%02x' % reg_num)
        mask = 0 if not ack else 1
        self.read_register_cmd.data = struct.pack('<BB', (reg_num << 3) | mask, 0)
        self.device.writecmd(self.read_register_cmd)
        resp = self.device.readcmd()
        reg_val = struct.unpack('<B', resp.data[1:2])[0]
        self.verbose('Read register 0x%02x has value 0x%02x' % (reg_num, reg_val))
        return reg_val

    def write_register(self, reg_num, value, ack=False):
        self.verbose('Writing register 0x%02x with value 0x%02x' % (reg_num, value))
        mask = 2 if not ack else 3
        self.write_register_cmd.data = struct.pack('<BB', (reg_num << 3) | mask, value)
        self.device.writecmd(self.write_register_cmd)
        self.device.readcmd()

    def get_version(self):
        return self.read_register(Regs.revision)

    def ack_status_stage(self):
        self.verbose('Sending ack!')
        self.device.writecmd(self.ack_cmd)
        self.device.readcmd()

    def connect(self, usb_device):
        super(Max342xPhy, self).connect(usb_device)
        self.write_register(Regs.usb_control, self.usb_control_vbgate | self.usb_control_connect)
        self.info('Connected device %s' % self.connected_device.name)

    def disconnect(self):
        self.write_register(Regs.usb_control, self.usb_control_vbgate)
        return super(Max342xPhy, self).disconnect()

    def clear_irq_bit(self, reg, bit):
        self.write_register(reg, bit)

    def read_bytes(self, reg, n):
        self.verbose('reading %d bytes from register %s' % (n, reg))
        data = struct.pack('B', reg << 3) + b'\00' * n
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        resp = self.device.readcmd()
        self.verbose('read %d bytes from register %d' % (len(resp.data) - 1, reg))
        return resp.data[1:]

    def write_bytes(self, reg, data):
        data = struct.pack('<B', (reg << 3) | 3) + data
        cmd = FacedancerCommand(self.app_num, 0x00, data)

        self.device.writecmd(cmd)
        self.device.readcmd()  # null response

        self.verbose('wrote %d bytes to register %d' % (len(data) - 1, reg))

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def send_on_endpoint(self, ep_num, data):
        if ep_num == 0:
            fifo_reg = Regs.ep0_fifo
            bc_reg = Regs.ep0_byte_count
        elif ep_num == 2:
            fifo_reg = Regs.ep2_in_fifo
            bc_reg = Regs.ep2_in_byte_count
        elif ep_num == 3:
            fifo_reg = Regs.ep3_in_fifo
            bc_reg = Regs.ep3_in_byte_count
        else:
            raise ValueError('endpoint ' + str(ep_num) + ' not supported')

        # FIFO buffer is only 64 bytes, must loop
        while len(data) > 64:
            self.write_bytes(fifo_reg, data[:64])
            self.write_register(bc_reg, 64, ack=True)

            data = data[64:]

        self.write_bytes(fifo_reg, data)
        self.write_register(bc_reg, len(data), ack=True)

        self.verbose('wrote %s to endpoint %#x' % (hexlify(data), ep_num))

    # HACK: but given the limitations of the MAX chips, it seems necessary
    def read_from_endpoint(self, ep_num):
        if ep_num != 1:
            return b''
        byte_count = self.read_register(Regs.ep1_out_byte_count)
        if byte_count == 0:
            return b''
        data = self.read_bytes(Regs.ep1_out_fifo, byte_count)
        self.verbose('read %s from endpoint %#x' % (hexlify(data), ep_num))
        return data

    def stall_ep0(self):
        self.verbose('stalling endpoint 0')
        self.write_register(Regs.ep_stalls, 0x23)

    def run(self):
        self.service_irqs()

    def service_irqs(self):
        while not self.stop:
            irq = self.read_register(Regs.endpoint_irq)

            self.verbose('read endpoint irq: 0x%02x' % irq)

            if irq & ~(
                self.is_in0_buffer_avail |
                self.is_in2_buffer_avail |
                self.is_in3_buffer_avail
            ):
                self.debug('notable irq: 0x%02x' % irq)

            if irq & self.is_setup_data_avail:
                self.clear_irq_bit(Regs.endpoint_irq, self.is_setup_data_avail)

                b = self.read_bytes(Regs.setup_data_fifo, 8)
                if (irq & self.is_out0_data_avail) and (ord(b[0]) & 0x80 == 0x00):
                    data_bytes_len = struct.unpack('<H', b[6:])[0]
                    b += self.read_bytes(Regs.ep0_fifo, data_bytes_len)
                self.connected_device.handle_request(b)

            if irq & self.is_out1_data_avail:
                data = self.read_from_endpoint(1)
                if data:
                    self.connected_device.handle_data_available(1, data)
                self.clear_irq_bit(Regs.endpoint_irq, self.is_out1_data_avail)

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
            if self.app.packet_processed():
                break

    # code that should be removed soon
    def usb_function_supported(self):
        self.app.usb_function_supported()
