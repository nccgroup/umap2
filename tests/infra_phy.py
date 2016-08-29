'''
Physical layer for testing umap2 core and devices
'''
from umap2.phy.iphy import PhyInterface
from infra_event_handler import TestEvent


class SendDataEvent(TestEvent):
    '''
    Event that signify data that is sent on an endpoint
    '''
    def __init__(self, ep_num, data):
        super(SendDataEvent, self).__init__()
        self.ep_num = ep_num
        self.data = data


class StallEp0Event(TestEvent):
    pass


class TestPhy(PhyInterface):
    '''
    Test physical interface
    '''
    def __init__(self, app):
        '''
        :type app: :class:`~umap2.app.base.Umap2App`
        :param app: application instance
        '''
        super(TestPhy, self).__init__(app, 'Test')

    def send_on_endpoint(self, ep_num, data):
        '''
        Send data on a specific endpoint

        :param ep_num: number of endpoint
        :param data: data to send
        '''
        self.app.event_handler.handle_event(SendDataEvent(ep_num, data))

    def stall_ep0(self):
        '''
        Stalls control endpoint (0)
        '''
        self.app.event_handler.handle_event(StallEp0Event())

    def run(self):
        '''
        Handle USB requests

        No real meaning at the moment, might change it later on
        '''
        pass
