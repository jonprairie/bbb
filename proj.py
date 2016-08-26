"""
representation of a project to be synchronized
"""
import os


class Proj:
    def __init__(self, name, host, user=None, pth=None):
        self.name = name
        if pth is not None and not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        elif pth is None:
            pth = os.path.abspath(name)
        self.pth = pth

        self.user = user
        self.host = host
        self.file_mappings = None
