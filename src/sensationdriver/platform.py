import os


def is_raspberry():
    return os.popen('uname').read() == 'Linux\n'
