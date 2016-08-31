'''
Common unit test functionality
'''
import logging
test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        # logger = logging.getLogger('unit_test_logs')
        logger = logging.getLogger('umap2')
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] -> %(message)s'
        )
        handler = logging.FileHandler('test.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger
