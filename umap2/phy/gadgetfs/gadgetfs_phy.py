'''
Emulate a USB device via GadgetFS (Linux only)

This module utilizes the GagdetFS module in Linux,
which allows a user-space applications to implement USB devices on supported
platforms by reading and writing into files.

Due to the blocking nature of the endpoint files, and since there is no
implementation for poll/select for the endpoints, we create a separate thread
for each endpoint when a USB host is connected to the device.

.. note::

    Before kernel v4.8, there was a bug in the sync i/o mechanism of the
    GadgetFS kernel module, and a patched module is required in order to use
    this feature with Umap2.

    Even in v4.8 GadgetFS requires valid descriptors to be set in order to use
    the module, and then caches them for further use. This means that you
    cannot perform fuzzing of the enumeration with this module unless you use
    the patched version of the kernel module (code available in this repo
    under gadget/inode.c, but might require some tinkering, depending on your
    kernel version).
'''
import platform
import time
import struct
import select
import os
from binascii import hexlify
import threading

from six.moves.queue import Queue, Empty

from umap2.core.usb import Request, DescriptorType
from umap2.core.usb_device import USBDeviceRequest
from umap2.core.usb_endpoint import USBEndpoint
from umap2.phy.iphy import PhyInterface


GFS_CMD_INIT_DEVICE = 0
GFS_CMD_INIT_EP = 1

GFS_EV_NOP = 0
GFS_EV_CONNECT = 1
GFS_EV_DISCONNECT = 2
GFS_EV_SETUP = 3
GFS_EV_SUSPEND = 4

GFS_EVENT_SIZE = 12

GFS_EVENT_TYPE_OFFSET = 8

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
        dlen, dtype = struct.unpack('BB', data[i:i + 2])
        if dtype == keep_dt:
            filtered += data[i:i + dlen]
        i += dlen
    return filtered


def set_highspeed_endpoints(dev):
    '''
    If we are in high-speed mode, and this is a bulk endpoint,
    use the high-speed max packet size.

    :param dev: USBDevice that will be modified
    '''
    for conf in dev.configurations:
        for iface in conf.interfaces:
            for ep in iface.endpoints:
                if ep.transfer_type == USBEndpoint.transfer_type_bulk:
                    ep.max_packet_size = ep._get_max_packet_size('highspeed')


class GadgetFsPhy(PhyInterface):
    '''
    Physical layer based on GadgetFS
    '''

    control_filenames = [
        'net2280',
        'gfs_udc',
        'pxa2xx_udc',
        'goku_udc',
        'sh_udc',
        'omap_udc',
        'musb-hdrc',
        'at91_udc',
        'lh740x_udc',
        'atmel_usba_udc',
        '20980000.usb',
    ]

    def __init__(self, app, gadgetfs_dir='/dev/gadget'):
        super(GadgetFsPhy, self).__init__(app, 'GadgetFsPhy')
        if platform.system() != 'Linux':
            raise Exception('GadgetFsPhy is only supported on Linux')
        self.gadgetfs_dir = gadgetfs_dir
        self.control_fd = None
        self.control_filename = self._get_control_filename()
        self.configured = False
        # we need to use separate thread for each endpoint ...
        self.ep_threads = {}
        self.in_ep_threads = []


    def _get_control_filename(self):
        '''
        Get the control filename, depending on the USB driver.
        If there's more than one, the first match (alphabetically)
        will be returned.

        :return: control (EP0) filename
        :raises: exception if no control file found
        '''
        for filename in os.listdir(self.gadgetfs_dir):
            if filename in GadgetFsPhy.control_filenames:
                full_path = os.path.join(self.gadgetfs_dir, filename)
                self.info('Found a control file: %s' % (full_path))
                return full_path
        raise Exception(
            'No control file found in %s. Is the gadgetfs driver loaded?' % (self.gadgetfs_dir)
        )

    def _is_high_speed(self):
        '''
        .. todo: implement
        '''
        return True

    def connect(self, device):
        super(GadgetFsPhy, self).connect(device)
        self.control_fd = os.open(self.control_filename, os.O_RDWR | os.O_NONBLOCK)
        self.debug('Opened control file: %s' % (self.control_filename))
        set_highspeed_endpoints(self.connected_device)
        buff = struct.pack('I', GFS_CMD_INIT_DEVICE)
        for conf in self.connected_device.configurations:
            buff += conf.get_descriptor(usb_type='fullspeed', valid=True)
            if self._is_high_speed():
                buff += conf.get_descriptor(usb_type='highspeed', valid=True)  # might need to specify USB version here...
        buff += self.connected_device.get_descriptor(valid=True)
        self.verbose('About to write %#x configuration bytes to control file (%d)' % (len(buff), self.control_fd))
        os.write(self.control_fd, buff)
        self.verbose('Write completed')

    def disconnect(self):
        # signal threads to stop the loop
        for _, t in self.ep_threads.items():
            t.stop_evt.set()
        # close all file descriptors
        fds = [t.ep.fd for (_, t) in self.ep_threads.items()]
        for fd in fds:
            os.close(fd)
            self.verbose('Closed fd: %d' % (fd))
        if self.control_fd:
            os.close(self.control_fd)
        self.control_fd = None
        # now, wait for all threads to complete
        for ep_address, t in self.ep_threads.items():
            self.verbose('closing thread for endpoint %#x' % (ep_address))
            t.join()
        self.ep_threads = {}
        self.in_ep_threads = []
        return super(GadgetFsPhy, self).disconnect()

    def run(self):
        '''
        run loop for handling control (endpoint 0) events
        '''
        self.debug('Started run loop')
        self.stop = False
        while not self.stop:
            ready_eps, _, _ = select.select([self.control_fd], [], [], 0.001)
            if ready_eps:
                self._handle_ep0()
            if self.app.should_stop_phy():
                self.stop = True
            for ept in self.in_ep_threads:
                if not ept.handling_write():
                    self.connected_device.handle_buffer_available(ept.ep.number)
        self.debug('Done with run loop')

    def send_on_endpoint(self, ep_num, data):
        self.debug('send_on_endpoint %d(%d): %s' % (ep_num, len(data), hexlify(data)))
        address = ep_num | 0x80
        if ep_num == 0:
            self.send_on_ep0(data)
        elif address in self.ep_threads:
            self.ep_threads[address].send(data)
        else:
            raise Exception('No IN endpoint %#x (address %#x)' % (ep_num, address))

    def send_on_ep0(self, data):
        if data:
            os.write(self.control_fd, data)
            self.debug('Done writing %d bytes to control endpoint (0)' % (len(data)))
        else:
            self.stall_ep0()

    def stall_ep0(self):
        self.debug('Stalling EP0')
        try:
            if self.req_direction == Request.direction_host_to_device:
                os.write(self.control_fd, b'')
            else:
                os.read(self.control_fd, 0)
        except OSError as oe:
            # 51: Level two halted (e.g. stalled)
            if oe.errno == 51:
                pass

    def _handle_ep0(self):
        # read event
        while True:
            try:
                events = os.read(self.control_fd, GFS_EVENT_SIZE * 5)
                break
            except OSError as ose:
                if ose.errno == 11:  # resource temporarily busy
                    time.sleep(0.01)
                    continue
                raise
        for i in range(0, len(events), GFS_EVENT_SIZE):
            event = events[i:i + GFS_EVENT_SIZE]
            if len(event) < GFS_EVENT_SIZE:
                msg = 'Did not read full event (%d/%d)' % (len(event), GFS_EVENT_SIZE)
                self.error(msg)
                raise Exception(msg)
            event_type = struct.unpack('<I', event[GFS_EVENT_TYPE_OFFSET:GFS_EVENT_TYPE_OFFSET + 4])[0]
            if event_type == GFS_EV_NOP:
                self._handle_ep0_nop(event)
            elif event_type == GFS_EV_CONNECT:
                self._handle_ep0_connect(event)
            elif event_type == GFS_EV_DISCONNECT:
                self._handle_ep0_disconnect(event)
            elif event_type == GFS_EV_SETUP:
                self._handle_ep0_setup(event)
            elif event_type == GFS_EV_SUSPEND:
                self._handle_ep0_suspend(event)
            else:
                self.warning('Got unknown event type for EP0 %#x' % (event_type))

    def _handle_ep0_nop(self, event):
        self.debug('EP0 event type NOP(%#x)' % (GFS_EV_NOP))

    def _handle_ep0_connect(self, event):
        self.debug('EP0 event type CONNECT(%#x)' % (GFS_EV_CONNECT))

    def _handle_ep0_disconnect(self, event):
        self.debug('EP0 event type DISCONNECT(%#x)' % (GFS_EV_DISCONNECT))

    def _handle_ep0_setup(self, event):
        self.debug('EP0 event type SETUP(%#x)' % (GFS_EV_SETUP))
        self.app.signal_setup_packet_received()
        # read setup data (offset in event)
        setup_data = event[:GFS_EVENT_TYPE_OFFSET]
        req = USBDeviceRequest(setup_data)
        self.req_direction = req.get_direction()
        if self.req_direction == Request.direction_host_to_device and req.length > 0:
            # Turns out, that at this point we cannot
            #
            self.debug(req)
            self.debug('expecting additional data on control ep - %#x bytes' % (req.length))
            data = os.read(self.control_fd, req.length)
            if len(data) != req.length:
                self.error('EP0 data have wrong length')
            else:
                req.data = data
        self.connected_device.handle_request(setup_data)
        self.configured = self.connected_device.configuration is not None

    def _setup_endpoints(self):
        conf = self.connected_device.configuration
        for iface in conf.interfaces:
            for ep in iface.endpoints:
                self._setup_endpoint(ep)

    def _setup_endpoint(self, ep):
        if self._ep_already_opened(ep):
            self._update_ep(ep)
        else:
            self._open_endpoint_fd(ep)
            buff = struct.pack('I', GFS_CMD_INIT_EP)
            descs = ep.get_descriptor(usb_type='fullspeed', valid=True)
            if self._is_high_speed():
                descs += ep.get_descriptor(usb_type='highspeed', valid=True)
            descs = filter_descriptors(descs, DescriptorType.endpoint)
            buff += descs
            os.write(ep.fd, buff)
            if ep.direction == USBEndpoint.direction_out:
                t = OutEpThread(self, ep)
            else:
                t = InEpThread(self, ep)
                self.in_ep_threads.append(t)
            self.ep_threads[ep.address] = t
            t.start()

    def _ep_already_opened(self, ep):
        return ep.address in self.ep_threads

    def _update_ep(self, ep):
        self.ep_threads[ep.address].ep = ep

    def _open_endpoint_fd(self, ep):
        '''
        :param ep: USBEndpoint object

        :raises Exception: if no endpoint file found, or failed to open

        .. todo:: detect transfer-type specific endpoint files
        '''
        num = ep.number
        s_dir = 'out' if ep.direction == USBEndpoint.direction_out else 'in'
        filename = 'ep%d%s' % (num, s_dir)
        path = os.path.join(self.gadgetfs_dir, filename)
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.debug('Opened endpoint %d' % (num))
        self.debug('ep: %d dir: %s file: %s fd: %d' % (num, s_dir, filename, fd))
        ep.fd = fd

    def _handle_ep0_suspend(self, event):
        self.debug('EP0 event type SUSPEND(%#x)' % (GFS_EV_SUSPEND))

    def ack_status_stage(self):
        os.read(self.control_fd, 0)
        self._setup_endpoints()


class EndpointThread(threading.Thread):
    '''Thread for endpoint I/O'''

    def __init__(self, phy, ep):
        super(EndpointThread, self).__init__()
        self.phy = phy
        self.ep = ep
        self.stop_evt = threading.Event()

    def run(self):
        self.phy.debug('Starting thread for EP %#x' % (self.ep.address))
        first = True
        while not self.stop_evt.isSet():
            try:
                self.io_op()
            except OSError as err:
                # bad fd, transport socket closed
                if err.errno in [9, 108] and first:
                    first = False
                    continue
                self.phy.error('Error in EP%d handling thread: %s' % (self.ep.number, err))


class InEpThread(EndpointThread):

    def __init__(self, phy, ep):
        super(InEpThread, self).__init__(phy, ep)
        self.queue = Queue()

    def send(self, data):
        self.queue.put(data)

    def handling_write(self):
        return not self.queue.empty()

    def io_op(self):
        '''
         Fetch data from send queue and write to endpoint
        '''
        try:
            data = self.queue.get(True, 0.1)
            os.write(self.ep.fd, data)
        except Empty:
            pass


class OutEpThread(EndpointThread):

    def __init__(self, phy, ep):
        super(OutEpThread, self).__init__(phy, ep)
        self.read_size = self.ep._get_max_packet_size('highspeed')

    def io_op(self):
        '''
        read data from endpoint fd and let the endpoint handle it
        '''
        self.phy.debug('About to read from EP%d' % (self.ep.number))
        buff = os.read(self.ep.fd, self.read_size)
        self.phy.debug('Done reading from EP%d' % (self.ep.number))
        self.phy.connected_device.handle_data_available(self.ep.number, buff)

