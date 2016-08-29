'''
Tests for emulated USB devices
'''

import unittest
import struct
from common import get_test_logger
from infra_event_handler import EventHandler
from infra_app import TestApp
from infra_phy import SendDataEvent, StallEp0Event


DIR_OUT = 0x00
DIR_IN = 0x80
TYPE_STANDARD = 0x00
TYPE_CLASS = 0x20
TYPE_VENDOR = 0x40
TYPE_RESERVED = 0x60
RECIPIENT_DEVICE = 0x00
RECIPIENT_INTERFACE = 0x01
RECIPIENT_ENDPOINT = 0x02
RECIPIENT_OTHER = 0x03

DEVICE_REQUEST_GET_STATUS = 0x00
DEVICE_REQUEST_CLEAR_FEATURE = 0x01
DEVICE_REQUEST_SET_FEATURE = 0x03
DEVICE_REQUEST_SET_ADDRESS = 0x05
DEVICE_REQUEST_GET_DESCRIPTOR = 0x06
DEVICE_REQUEST_SET_DESCRIPTOR = 0x07
DEVICE_REQUEST_GET_CONFIGURATION = 0x08
DEVICE_REQUEST_SET_CONFIGURATION = 0x09

INTERFACE_REQUEST_GET_STATUS = 0x00
INTERFACE_REQUEST_CLEAR_FEATURE = 0x01
INTERFACE_REQUEST_SET_FEATURE = 0x03
INTERFACE_REQUEST_GET_INTERFACE = 0x0A
INTERFACE_REQUEST_SET_INTERFACE = 0x11

ENDPOINT_REQUEST_GET_STATUS = 0x00
ENDPOINT_REQUEST_CLEAR_FEATURE = 0x01
ENDPOINT_REQUEST_SET_FEATURE = 0x03
ENDPOINT_REQUEST_SYNCH_FRAME = 0x12

DESCRIPTOR_TYPE_DEVICE = 0x01
DESCRIPTOR_TYPE_CONFIGURATION = 0x02
DESCRIPTOR_TYPE_INTERFACE = 0x04
DESCRIPTOR_TYPE_ENDPOINT = 0x05
DESCRIPTOR_TYPE_STRING = 0x0
DESCRIPTOR_TYPE_DEVICE_QUALIFIER = 0x006

DESCRIPTOR_LENGTH_DEVICE = 0x12
DESCRIPTOR_LENGTH_CONFIGURATION = 0x09
DESCRIPTOR_LENGTH_INTERFACE = 0x09
DESCRIPTOR_LENGTH_ENDPOINT = 0x07
DESCRIPTOR_LENGTH_STRING = 0x02   # base size
DESCRIPTOR_LENGTH_DEVICE_QUALIFIER = 0x006


def setup_request(
    s_dir,
    s_type,
    s_recipient,
    s_request,
    s_desc_index,
    s_desc_type,
    s_lang_id,
    s_length=None,
    s_data=None
):
    if s_length is None:
        if s_data is not None:
            s_length == len(s_data)
        else:
            raise Exception('Need some length :(')
    s = struct.pack(
        '<BBBBHH',
        s_dir | s_type | s_recipient,
        s_request,
        s_desc_index,
        s_desc_type,
        s_lang_id,
        s_length
    )
    if s_data:
        s += s_data
    return s


def build_get_device_descriptor():
    return setup_request(
        DIR_IN, TYPE_STANDARD, RECIPIENT_DEVICE, DEVICE_REQUEST_GET_DESCRIPTOR,
        0, DESCRIPTOR_TYPE_DEVICE, 0, DESCRIPTOR_LENGTH_DEVICE
    )


def build_get_configuration_descriptor(idx, length=DESCRIPTOR_LENGTH_CONFIGURATION):
    return setup_request(
        DIR_IN, TYPE_STANDARD, RECIPIENT_DEVICE, DEVICE_REQUEST_GET_DESCRIPTOR,
        idx, DESCRIPTOR_TYPE_CONFIGURATION, 0, length
    )


def build_get_string_descriptor(idx, language_id=0x0403, length=0xff):
    return setup_request(
        DIR_IN, TYPE_STANDARD, RECIPIENT_DEVICE, DEVICE_REQUEST_GET_DESCRIPTOR,
        idx, DESCRIPTOR_TYPE_STRING, language_id, length
    )


class BaseDeviceTests(object):

    __dev_name__ = None

    def _setUp(self):
        self.logger = get_test_logger()
        self.events = EventHandler()
        self.app = TestApp(event_handler=self.events)
        self.logger.info('Starting test: %s' % self._testMethodName)
        self.phy = self.app.load_phy('test')
        self.device = self.app.load_device(self.__dev_name__, self.phy)

    def send_control_message(self, data):
        self.device.handle_request(data)

    def send_data_to_endpoint(self, ep_num, data):
        self.device.handle_data_available(ep_num, data)

    def get_single_response(self, ep_num, response_length=None, max_respone_length=None):
        self.assertEquals(len(self.events.events), 1)
        ev = self.events.events.pop()
        self.assertTrue(isinstance(ev, SendDataEvent))
        self.assertEqual(ev.ep_num, 0)
        if response_length is not None:
            self.assertEqual(len(ev.data), response_length)
        else:
            self.assertEqual(len(ev.data), max_respone_length)
        return ev

    def _testGetDescriptorConsistent(self, request, response_length):
        self.device.handle_request(request)
        ev1 = self.get_single_response(0, response_length)
        self.device.handle_request(request)
        ev2 = self.get_single_response(0, response_length)
        self.assertEqual(ev1.data, ev2.data)

    def testGetDeviceDescriptorConsistent(self):
        self._testGetDescriptorConsistent(build_get_device_descriptor(), DESCRIPTOR_LENGTH_DEVICE)

    def testGetConfigurationDescriptorConsistent(self):
        self.device.handle_request(build_get_device_descriptor())
        self.get_single_response(0, DESCRIPTOR_LENGTH_DEVICE)
        self._testGetDescriptorConsistent(build_get_configuration_descriptor(0), DESCRIPTOR_LENGTH_CONFIGURATION)


class AudioDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'audio'

    def setUp(self):
        self._setUp()


class CdcAcmDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'cdc_acm'

    def setUp(self):
        self._setUp()


class FtdiDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'ftdi'

    def setUp(self):
        self._setUp()


class HubDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'hub'

    def setUp(self):
        self._setUp()


class KeyboardDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'keyboard'

    def setUp(self):
        self._setUp()


class PrinterDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'printer'

    def setUp(self):
        self._setUp()


class SmartcardDeviceTests(unittest.TestCase, BaseDeviceTests):

    __dev_name__ = 'smartcard'

    def setUp(self):
        self._setUp()
