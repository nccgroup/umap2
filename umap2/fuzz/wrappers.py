import traceback
import binascii


def mutable(stage, silent=False):
    def wrap_f(func):
        def wrapper(self, *args, **kwargs):
            info = self.info if not silent else self.debug
            session_data = self.get_session_data(stage)
            data = kwargs.get('fuzzing_data', {})
            data.update(session_data)
            response = self.get_mutation(stage=stage, data=data)
            try:
                if response is not None:
                    if not silent:
                        info('Got mutation for stage %s' % stage)
                else:
                    info('Calling %s (stage: "%s")' % (func.__name__, stage))
                    response = func(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(traceback.format_exc())
                self.logger.error(''.join(traceback.format_stack()))
                raise e
            if response is not None:
                info('Response: %s' % binascii.hexlify(response))
            return response
        return wrapper
    return wrap_f
