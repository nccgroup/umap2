import struct
import select
import os
import sys
from binascii import hexlify
import threading

from umap2.core.usb import Request, DescriptorType
from umap2.core.usb_device import USBDeviceRequest
from umap2.phy.iphy import PhyInterface


class Tags(object):
    INIT_DEVICE = 0
    INIT_EP = 1


class Events(object):
    NOP = 0
    CONNECT = 1
    DISCONNECT = 2
    SETUP = 3
    SUSPEND = 4


def filter_descriptors(data, keep_dt):
    '''
    Keep only descriptors with given descriptor type

    :param data: descriptors buffer
    :param keep_dt: type of descriptor to keep
    :return: buffer only with keep_dt descriptors
    '''
    i = 0
    filtered = ''
    while i < len(data) - 2:
        l, dt = struct.unpack('BB', data[i:i + 2])
        if dt == keep_dt:
            filtered += data[i:i + l]
        i += l
    return filtered


def set_highspeed_endpoints(dev):
    for conf in dev.configurations:
        for iface in conf.interfaces:
            for ep in iface.endpoints:
                if ep.transfer_type == 0x2:  # BULK
                    ep.max_packet_size = ep._get_max_packet_size('highspeed')


class GadgetFsPhy(PhyInterface):
    '''
    Physical layer based on GadgetFS
    '''

    control_filenames = [
        "net2280",
        "gfs_udc",
        "pxa2xx_udc",
        "goku_udc",
        "sh_udc",
        "omap_udc",
        "musb-hdrc",
        "at91_udc",
        "lh740x_udc",
        "atmel_usba_udc",
    ]

    event_size = 12
    event_type_off = 8

    def __init__(self, app, gadgetfs_dir='/dev/gadget'):
        super(GadgetFsPhy, self).__init__(app, 'GadgetFsPhy')
        if sys.platform not in ['linux', 'linux2']:
            raise Exception('GadgetFsPhy is only supported on Linux')
        self.gadgetfs_dir = gadgetfs_dir
        self.control_fd = None
        self.in_ep_fds = []
        self.fd_ep_mapping = {}
        self.ep_fd_mapping = {}
        self.control_filename = self._get_control_filename()
        self.configured = False
        # we need to use separate thread for each endpoint ...
        self.out_ep_threads = {}
        

    def _get_control_filename(self):
        '''
        Get the control filename, depending on the USB driver.
        If there's more than one, the first match (alphabetically)
        will be returned.

        :return: control (EP0) filename
        :raises: exception if no control file found
        '''
        for f in os.listdir(self.gadgetfs_dir):
            if f in GadgetFsPhy.control_filenames:
                full_path = os.path.join(self.gadgetfs_dir, f)
                self.info('Found a control file: %s' % (full_path))
                return full_path
        raise Exception(
            'No known control file found in %s. Is the gadgetfs driver loaded?' % (self.gadgetfs_dir)
        )

    def _is_high_speed(self):
        '''
        .. todo: implement
        '''
        return True

    def connect(self, device):
        super(GadgetFsPhy, self).connect(device)
        self.control_fd = os.open(self.control_filename, os.O_RDWR | os.O_NONBLOCK)
        self.fd_ep_mapping[self.control_fd] = 0
        self.ep_fd_mapping[0] = self.control_fd
        self.debug('Opened control file: %s' % (self.control_filename))
        set_highspeed_endpoints(self.connected_device)
        buff = struct.pack('I', Tags.INIT_DEVICE)
        for conf in self.connected_device.configurations:
            buff += conf.get_descriptor(usb_type='fullspeed', valid=True)
            if self._is_high_speed():
                buff += conf.get_descriptor(usb_type='highspeed', valid=True)  # might need to specify USB version here...
        buff += self.connected_device.get_descriptor(valid=True)
        self.debug('About to write %#x configuration bytes to control file (%d)' % (len(buff), self.control_fd))
        os.write(self.control_fd, buff)
        self.debug('Write completed')

    def disconnect(self):
        self.control_fd = None
        ep_nums = self.out_ep_threads.keys()
        for ep_num in ep_nums:
            self.out_ep_threads[ep_num].stop_evt.set()
            del self.out_ep_threads[ep_num]
        fds = self.fd_ep_mapping.keys()
        for fd in fds:
            os.close(fd)
            self.debug('Closed fd: %d' % (fd))
            del self.fd_ep_mapping[fd]
        self.ep_fd_mapping = {}
        self.in_ep_fds = []
        return super(GadgetFsPhy, self).disconnect()

    def run(self):
        self.debug('Started run loop')
        self.stop = False
        while not self.stop:
            # EP0 read and IN endpoints write thread.
            ready_out_eps, _, _ = select.select([self.control_fd], [], [], 0.001)
            for ep_fd in ready_out_eps:
                ep_num = self.fd_ep_mapping[ep_fd]
                self._handle_ep0()
                if self.app.packet_processed():
                    self.stop = True
            for ep_fd in self.in_ep_fds:
                self.connected_device.handle_buffer_available(self.fd_ep_mapping[ep_fd])
        self.debug('Done with run loop')

    def send_on_endpoint(self, ep_num, data):
        '''
        .. todo: make sure this is an IN endpoint
        '''
        self.debug('send_on_endpoint %d(%d): %s' % (ep_num, len(data), hexlify(data)))
        if data:
            fd = self.ep_fd_mapping[ep_num]
            os.write(fd, data)
            self.debug('Done writing %d bytes on endpoint %d' % (len(data), ep_num))
        elif ep_num == 0:
            self.debug('No data, stalling ep0')
            self.stall_ep0()

    def stall_ep0(self):
        self.info('Stalling EP0')
        try:
            os.read(self.control_fd, 0)
        except OSError as oe:
            # 51: Level two halted (e.g. stalled)
            if oe.errno == 51:
                pass

    def _handle_ep0(self):
        # read event
        event = os.read(self.control_fd, GadgetFsPhy.event_size)
        if len(event) != GadgetFsPhy.event_size:
            msg = 'Did not read full event (%d/%d)' % (len(event), GadgetFsPhy.event_size)
            self.error(msg)
            raise Exception(msg)
        event_type = struct.unpack('<I', event[GadgetFsPhy.event_type_off:GadgetFsPhy.event_type_off + 4])[0]
        if event_type == Events.NOP:
            self._handle_ep0_nop(event)
        elif event_type == Events.CONNECT:
            self._handle_ep0_connect(event)
        elif event_type == Events.DISCONNECT:
            self._handle_ep0_disconnect(event)
        elif event_type == Events.SETUP:
            self._handle_ep0_setup(event)
        elif event_type == Events.SUSPEND:
            self._handle_ep0_suspend(event)
        else:
            self.warning('Got unknown event type for EP0 %#x' % (event_type))

    def _handle_ep0_nop(self, event):
        self.debug('EP0 event type NOP(%#x)' % (Events.NOP))

    def _handle_ep0_connect(self, event):
        self.debug('EP0 event type CONNECT(%#x)' % (Events.CONNECT))

    def _handle_ep0_disconnect(self, event):
        self.debug('EP0 event type DISCONNECT(%#x)' % (Events.DISCONNECT))

    def _handle_ep0_setup(self, event):
        self.debug('EP0 event type SETUP(%#x)' % (Events.SETUP))
        # read setup data (offset in event)
        setup_data = event[0:GadgetFsPhy.event_type_off]
        req = USBDeviceRequest(setup_data)
        if req.get_direction() == Request.direction_host_to_device and req.length > 0:
            self.warning('EP0 needs to read more data - is this supported by gadgetfs ???')
            # TODO: test this with audio device
        self.connected_device.handle_request(setup_data)
        if not self.configured:
            if self.connected_device.configuration:
                self.configured = True
                # self._setup_endpoints()
        else:
            if not self.connected_device.configuration:
                # .. todo: remove endpoints
                # maybe it should be in the disconnect case
                self.configured = False

    def _setup_endpoints(self):
        conf = self.connected_device.configuration
        for iface in conf.interfaces:
            for ep in iface.endpoints:
                self._setup_endpoint(ep)

    def _setup_endpoint(self, ep):
        ep_fd = self._get_endpoint_fd(ep)
        ep_num = ep.number
        self.fd_ep_mapping[ep_fd] = ep_num
        self.ep_fd_mapping[ep_num] = ep_fd
        buff = struct.pack('I', Tags.INIT_EP)
        descs = ep.get_descriptor(usb_type='fullspeed', valid=True)
        if self._is_high_speed():
            descs += ep.get_descriptor(usb_type='highspeed', valid=True)
        descs = filter_descriptors(descs, DescriptorType.endpoint)
        buff += descs
        os.write(ep_fd, buff)
        if ep.direction == 0:
            self.out_ep_threads[ep_num] = OutEpThread(self, ep_fd, ep)
            self.out_ep_threads[ep_num].start()
        else:
            self.in_ep_fds.append(ep_fd)

    def _get_endpoint_fd(self, ep):
        '''
        :param ep: USBEndpoint object

        :return: endpoint file descriptor
        :raises Exception: if no endpoint file found, or failed to open

        .. todo: detect transfer-type specific endpoint files
        '''
        num = ep.number
        s_dir = 'out' if ep.direction == 0 else 'in'
        filename = 'ep%d%s' % (num, s_dir)
        path = os.path.join(self.gadgetfs_dir, filename)
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.debug('Opened endpoint %d' % (num))
        self.debug('ep: %d dir: %s file: %s fd: %d' % (num, s_dir, filename, fd))
        return fd

        
    def _handle_ep0_suspend(self, event):
        self.debug('EP0 event type SUSPEND(%#x)' % (Events.SUSPEND))

    def ack_status_stage(self):
        self._setup_endpoints()
        os.read(self.control_fd, 0)


class OutEpThread(threading.Thread):

    def __init__(self, phy, fd, ep):
        super(OutEpThread, self).__init__()
        self.phy = phy
        self.stop_evt = threading.Event()
        self.fd = fd
        self.ep = ep
        self.read_size = self.ep._get_max_packet_size('highspeed')

    def run(self):
        first = True
        while not self.stop_evt.isSet():
            try:
                self.phy.debug('About to read from EP%d' % (self.ep.number))
                buff = os.read(self.fd, self.read_size)
                self.phy.debug('Done reading from EP%d' % (self.ep.number))
                self.phy.connected_device.handle_data_available(self.ep.number, buff)
            except OSError as err:
                # bad fd, transport socket closed
                if err.errno in [9, 108] and first:
                    first = False
                    continue
                self.phy.error('Error in EP%d handling thread: %s' % (self.ep.number, err))
