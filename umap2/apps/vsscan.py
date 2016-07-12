'''
Scan for vendor specific device support in USB host

Usage:
    umap2vsscan -P=PHY_INFO [-q] [-d=kernel_vid_pid.py] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -v --verbose                verbosity level
    -q --quiet                  quiet mode. only print warning/error messages
    -d --db						db file of {(vid, pid):(name,source_line)

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port

Example:
    umap2vsscan -P fd:/dev/ttyUSB0 -q
'''
import time
import traceback
import os
import sys
from umap2.apps.base import Umap2App


class Umap2VSScanApp(Umap2App):

    def __init__(self, options):
        super(Umap2VSScanApp, self).__init__(options)
        self.current_usb_function_supported = False
        self.start_time = 0

    def usb_function_supported(self):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.
        '''
        self.current_usb_function_supported = True

    def run(self):
        self.logger.always('Scanning host for supported vendor specific devices')
        phy = self.load_phy(self.options['--phy'])
        supported = []
        device_name = 'vendor_specific'
        db_list = {(0x05ac, 0x1402): ('Apple, Inc.', 'drivers/net/usb/asix_devices.c:1065'), (0x0a5c, 0x21e6): ('Broadcom Corp.', 'bt usb')}
        db_file = self.options['--db']
        if db_file:
            self.logger.info('loading vid_pid db file: %s' % db_file)
            dirpath, filename = os.path.split(db_file)
            modulename = filename[:-3]
            if dirpath in sys.path:
                sys.path.remove(dirpath)
            sys.path.insert(0, dirpath)
            module = __import__(modulename, globals(), locals(), [], -1)
            db_list = module.db

        for vid, pid in db_list:
            self.logger.always('Testing support for %s vid: %02x pid: %02x' % (device_name, vid, pid))
            try:
                self.start_time = time.time()
                device = self.load_device(device_name, phy)
                device.set_vid(vid)
                device.set_pid(pid)
                device.connect()
                device.run()
                device.disconnect()
            except:
                self.logger.error(traceback.format_exc())
            phy.disconnect()
            if self.current_usb_function_supported:
                self.logger.always('Device is SUPPORTED')
                supported.append((vid, pid))
            self.current_usb_function_supported = False
            self.num_processed = 0
            time.sleep(2)
        if len(supported):
            self.logger.always('---------------------------------')
            self.logger.always('Found %s supported device(s):' % (len(supported)))
            for i, vid_pid in enumerate(supported):
                self.logger.always('%d. vid: %04x, pid: %04x' % (i + 1, vid_pid[0], vid_pid[1]))

    def packet_processed(self):
        self.num_processed += 1
        stop_phy = False
        if self.num_processed == 3000:
            self.logger.info('Reached %#x packets, stopping phy' % self.num_processed)
            stop_phy = True
        elif time.time() - self.start_time > 5:
            self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (int(time.time() - self.start_time)))
            stop_phy = True
        return stop_phy


def main():
    app = Umap2VSScanApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
