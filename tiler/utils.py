import time
import subprocess
import sys

# Stolen from here:
# https://www.andreas-jung.com/contents/a-python-decorator-for-measuring-the-execution-time-of-methods
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('Timed {} {} took {}'.format(method.__name__, args, te-ts))
        return result
    return timed


@timeit
def check_call(*args, **kwargs):
    subprocess.check_call(*args, **kwargs)


@timeit
def check_output(*args, **kwargs):
    return subprocess.check_output(*args, **kwargs)


def stream_output(*args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    process = subprocess.Popen(*args, **kwargs)
    for c in iter(lambda: process.stdout.read(1), ''):
        sys.stdout.write(c)

    ret = process.wait()
    if ret != 0:
        raise subprocess.CalledProcessError(ret, " ".join(*args))
