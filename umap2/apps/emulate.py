#!/usr/bin/env python
'''
Emulate a USB device

Usage:
    umap2emulate -P=PHY_INFO -C=DEVICE_CLASS [-q] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -C --class DEVICE_CLASS     class of the device or path to python file with device class
    -v --verbose                verbosity level
    -q --quiet                  quiet mode. only print warning/error messages

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port

Examples:
    emulate keyboard:
        umap2emulate -P fd:/dev/ttyUSB1 -C keyboard
    emulate your own device:
        umap2emulate -P fd:/dev/ttyUSB1 -C my_usb_device.py
'''
import traceback

from umap2.apps.base import Umap2App


class Umap2EmulationApp(Umap2App):

    def run(self):
        self.fuzzer = self.get_fuzzer()
        self.phy = self.load_phy(self.options['--phy'], self.fuzzer)
        self.dev = self.load_device(self.options['--class'], self.phy)
        try:
            self.dev.connect()
            self.dev.run()
        except KeyboardInterrupt:
            self.logger.info('user terminated the run')
        except:
            self.logger.error('Got exception while connecting/running device')
            self.logger.error(traceback.format_exc())
        self.dev.disconnect()

    def get_fuzzer(self):
        return None


def main():
    app = Umap2EmulationApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
