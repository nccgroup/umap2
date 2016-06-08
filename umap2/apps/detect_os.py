'''
Try to detect OS based on the USB traffic.
Not implemented yet.

Usage:
    umap2detect -P=PHY_INFO [-q] [-v ...]

Options:
    -P --phy PHY_INFO           physical layer info, see list below
    -v --verbose                verbosity level
    -q --quiet                  quiet mode. only print warning/error messages

Physical layer:
    fd:<serial_port>        use facedancer connected to given serial port

Example:
    umap2detect -P fd:/dev/ttyUSB0 -q
'''
from umap2.apps.base import Umap2App


class Umap2DetectOSApp(Umap2App):

    def run(self):
        self.logger.error('OS detection is not implemented yet')


def main():
    app = Umap2DetectOSApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
