import logging
from umap2.apps.base import Umap2App
from umap2.utils.ulogger import set_default_handler_level
from infra_phy import TestPhy


class TestApp(Umap2App):

    def __init__(self, docstring=None, event_handler=None):
        super(TestApp, self).__init__(docstring)
        set_default_handler_level(logging.ERROR)
        self.event_handler = event_handler

    def load_phy(self, phy_string):
        if phy_string == 'test':
            return TestPhy(self)
        return super(TestApp, self).load_phy()

    def signal_setup_packet_received(self):
        '''
        Signal that we received a setup packet from the host (host is alive)
        '''
        self.event_handler.signal_setup_packet_received(self)
        self.setup_packet_received = True

    def should_stop_phy(self):
        '''
        :return: whether phy should stop serving.
        '''
        return False

    def usb_function_supported(self, reason=None):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.
        By default, do nothing with this information
        '''
        pass

    def get_mutation(self, stage, data=None):
        '''
        mutation is only needed when fuzzing
        '''
        return None
