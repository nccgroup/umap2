'''
Common functionality for all USB actors (interface, class, etc.)
'''
import time
import logging

start_time = time.time()


class USBBaseActor(object):

    name = 'Actor'

    def __init__(self, app, phy):
        '''
        :param app: Umap2 application
        :param phy: Physical connection
        '''
        self.phy = phy
        self.app = app
        self.session_data = {}
        self.str_dict = {}
        self.logger = logging.getLogger('umap2')

    def get_mutation(self, stage, data=None):
        '''
        :param stage: stage name
        :param data: dictionary (string: bytearray) of data for the fuzzer (default: None)
        :return: mutation for current stage, None if not current fuzzing stage
        '''
        return self.app.get_mutation(stage, data)

    def send_on_endpoint(self, ep, data):
        '''
        Send data on a given endpoint

        :param ep: endpoint number
        :param data: data to send
        '''
        self.phy.send_on_endpoint(ep, data)

    def get_session_data(self, stage):
        '''
        If an entity wants to pass specific data to the fuzzer when getting a mutation,
        it could return a session data here.
        This session data should be a dictionary of string:bytearray.
        The keys of the dictionary should match the keys in the templates.

        :param stage: stage that the session data is for
        :return: dictionary of session data
        '''
        return self.session_data

    def usb_function_supported(self, reason=None):
        '''
        Mark current USB function as supported by the host.
        This will tell the application to stop emulating current device.

        :param reason: reason why we decided it is supported (default: None)
        '''
        self.app.usb_function_supported(reason)

    def add_string_with_id(self, str_id, s):
        '''
        Add a string to the string dictionary

        :param str_id: id of the string
        :param s: the string
        '''
        self.str_dict[str_id] = s

    def get_string_by_id(self, str_id):
        '''
        Get a string by it's id

        :param str_id: string id
        :return: the string, or None if id does not exist
        '''
        self.debug('Getting string by id %#x' % (str_id))
        if str_id in self.str_dict:
            return self.str_dict[str_id]
        return None

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.name, msg), *args, **kwargs)
