import logging

stdio_handler = None
umap2_logger = None


def prepare_logging():
    global umap2_logger
    global stdio_handler
    if umap2_logger is None:
        def add_debug_level(num, name):
            def fn(self, message, *args, **kwargs):
                if self.isEnabledFor(num):
                    self._log(num, message, args, **kwargs)
            logging.addLevelName(num, name)
            setattr(logging, name, num)
            return fn

        logging.Logger.verbose = add_debug_level(5, 'VERBOSE')
        logging.Logger.always = add_debug_level(100, 'ALWAYS')

        FORMAT = '[%(levelname)-6s] %(message)s'
        stdio_handler = logging.StreamHandler()
        stdio_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(FORMAT)
        stdio_handler.setFormatter(formatter)
        umap2_logger = logging.getLogger('umap2')
        umap2_logger.addHandler(stdio_handler)
        umap2_logger.setLevel(logging.VERBOSE)
    return umap2_logger


def set_default_handler_level(level):
    global stdio_handler
    stdio_handler.setLevel(level)
