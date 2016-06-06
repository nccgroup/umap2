#
# Add debug levels/functions
#
import logging


def prepare_logging():
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
    logging.basicConfig(format=FORMAT)
    logger = logging.getLogger('umap2')
    logger.setLevel(logging.INFO)


prepare_logging()
