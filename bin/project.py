import os

def relative_path(*segments):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', *segments)
