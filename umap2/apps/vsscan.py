'''
Scan for vendor specific device support in USB host

Usage:
    umap2vsscan -P=PHY_INFO [-q] [-d=kernel_vid_pid.py] [-s=VID:PID] [-t=TIMEOUT] [-z] [-r=RESUME_FILE] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -v --verbose                verbosity level
    -q --quiet                  quiet mode. only print warning/error messages
    -d --db						db file of {(vid, pid):(name,source_line)
    -s --vid_pid VID:PID        specific VID:PID combination scan
    -t --timeout TIMEOUT        seconds to wait for host to detect each device (defualt: 3)
    -r --resume RESUME_FILE     filename to store/load scan session data
    -z --single_step            wait for keypress between each test

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port

Example:
    umap2vsscan -P fd:/dev/ttyUSB0 -q
    umap2vsscan -P fd:/dev/ttyUSB0 -s=2058:1005 -d=5
'''
import time
import traceback
import os
import signal
import sys
import cPickle
from umap2.apps.base import Umap2App
from umap2.dev.vendor_specific import USBVendorSpecificDevice


class ScanSession(object):

    def __init__(self):
        self.timeout = 5
        self.db = {}
        self.supported = {}
        self.unsupported = {}
        self.current = 0


class Umap2VSScanApp(Umap2App):

    def __init__(self, options):
        super(Umap2VSScanApp, self).__init__(options)
        self.current_usb_function_supported = False
        self.scan_session = ScanSession()
        self.start_time = 0
        self.stop_signal_recived = False
        signal.signal(signal.SIGINT, self.signal_handler)
        timeout = self.options['--timeout']
        if timeout:
            self.scan_session.timeout = int(timeout)
        self.single_step = False
        if self.options['--single_step']:
            self.single_step = True

    def usb_function_supported(self):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.
        '''
        self.current_usb_function_supported = True

    def signal_handler(self, signal, frame):
        self.stop_signal_recived = True

    def get_device_info(self, device):
        info = []
        if device.endpoints:
            for e in device.endpoints.keys():
                info.append(device.endpoints[e].get_descriptor())
        else:
            info = ''
        if info:
            return 'num_endpoints = %d' % len(info)
        else:
            return 'device not reached set configuration state'

    def run(self):
        self.logger.always('Scanning host for supported vendor specific devices')
        phy = self.load_phy(self.options['--phy'])
        # db_list = {(0x05ac, 0x1402): ('Apple, Inc.', 'drivers/net/usb/asix_devices.c:1065'), (0x0a5c, 0x21e6): ('Broadcom Corp.', 'bt usb')}
        # db_list = {(0x0a5c, 0x21e6): ('Broadcom Corp.', 'bt usb')}

        resume_file = self.options['--resume']
        if resume_file and os.path.exists(resume_file):
                self.logger.always('Resume file found. Loading scan data')
                with open(resume_file, 'rb') as rf:
                    self.scan_session = cPickle.load(rf)
        else:
            db_file = self.options['--db']
            vid_pid = self.options['--vid_pid']
            self.logger.always('Resume file not found. Creating new one')
            if db_file and vid_pid:
                self.logger.warning('not expecting both db file and specific vid:pid. we will use vid:pid')
            if vid_pid:
                vid, pid = vid_pid.split(':')
                vid = int(vid, 16)
                pid = int(pid, 16)
                vid_pid = (vid, pid)
                self.scan_session.db = {vid_pid: ('User Specified', 'User Specified')}
            elif db_file:
                self.logger.info('loading vid_pid db file: %s' % db_file)
                dirpath, filename = os.path.split(db_file)
                modulename = filename[:-3]
                if dirpath in sys.path:
                    sys.path.remove(dirpath)
                sys.path.insert(0, dirpath)
                module = __import__(modulename, globals(), locals(), [], -1)
                self.scan_session.db = module.db
                self.logger.always('loaded %d entries' % len(self.scan_session.db))
            else:
                self.logger.error('Must select a scan option - db (-d) or specific vid:pid (-p)')
                return

        while self.scan_session.current < (len(self.scan_session.db)):
            if self.stop_signal_recived:
                break
            vid, pid = self.scan_session.db.keys()[self.scan_session.current]
            vendor = self.scan_session.db[(vid, pid)][0]
            driver = self.scan_session.db[(vid, pid)][1]
            self.logger.always('Testing support for vid:pid %04x:%04x (vendor: %s, driver: %s)' % (vid, pid, vendor, driver))
            try:
                self.setup_packet_received = False
                self.current_usb_function_supported = False
                self.num_processed = 0
                self.start_time = time.time()
                device = USBVendorSpecificDevice(self, phy, vid, pid)
                device.connect()
                device.run()
                device.disconnect()
                if not self.setup_packet_received:
                    self.logger.error('Host appears to have died or is simply ignoring us :(')
                    break
            except:
                self.logger.error(traceback.format_exc())
            if self.current_usb_function_supported:
                device_info = self.get_device_info(device)
                self.scan_session.supported[(vid, pid)] = (vendor, driver, device_info)
            else:
                device_info = self.get_device_info(device)
                self.scan_session.unsupported[(vid, pid)] = (vendor, driver, device_info)
            self.scan_session.current += 1
            if resume_file:
                with open(resume_file, 'wb') as rf:
                    cPickle.dump(self.scan_session, rf, 2)
            if self.single_step:
                raw_input('press any key to continue')
            else:
                time.sleep(5)
        num_supported = len(self.scan_session.supported)
        num_unsupported = len(self.scan_session.unsupported)
        # if num_supported:
        self.logger.always('---------------------------------')
        self.logger.always('Found %s supported device(s) (out of %d):' % (num_supported, self.scan_session.current))
        for i, vid_pid in enumerate(self.scan_session.supported):
            vid = vid_pid[0]
            pid = vid_pid[1]
            vendor = self.scan_session.supported[(vid, pid)][0]
            driver = self.scan_session.supported[(vid, pid)][1]
            device_info = self.scan_session.supported[(vid, pid)][2]
            self.logger.always('%d. vid:pid %04x:%04x (vendor: %s, driver: %s, device_info: %s)' % (i + 1, vid, pid, vendor, driver, device_info))
        self.logger.always('Found %s unsupported device(s) (out of %d):' % (num_unsupported, self.scan_session.current))
        for i, vid_pid in enumerate(self.scan_session.unsupported):
            vid = vid_pid[0]
            pid = vid_pid[1]
            vendor = self.scan_session.unsupported[(vid, pid)][0]
            driver = self.scan_session.unsupported[(vid, pid)][1]
            device_info = self.scan_session.unsupported[(vid, pid)][2]
            self.logger.always('%d. vid:pid %04x:%04x (vendor: %s, driver: %s, device_info: %s)' % (i + 1, vid, pid, vendor, driver, device_info))

    def packet_processed(self):
        self.num_processed += 1
        stop_phy = False
        time_elapsed = int(time.time() - self.start_time)
        if self.current_usb_function_supported:
            stop_phy = True
        elif self.num_processed == 3000:
            self.logger.info('Reached %#x packets, stopping phy' % self.num_processed)
            stop_phy = True
        elif time_elapsed > self.scan_session.timeout:
            self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (time_elapsed))
            stop_phy = True
        return stop_phy


def main():
    app = Umap2VSScanApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
