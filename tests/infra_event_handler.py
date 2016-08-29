import time


class TestEvent(object):

    def __init__(self):
        self.time = time.time()


class EventHandler(object):

    def __init__(self):
        self.events = []

    def reset(self):
        self.events = []

    def handle_event(self, event):
        self.events.append(event)
