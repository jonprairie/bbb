"""
representation of a project to be synchronized
"""
import os


class Proj:
    def __init__(self, name, host=None, user=None, pth=None):
        self.name = name
        if pth is not None and not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        elif pth is None:
            pth = os.path.abspath(name)
        self.pth = pth

        self.user = user
        self.host = host

        self.local_to_host = dict()
        self.host_to_local = dict()

    def add_tracker(self, host_fl=None, local_fl=None):
        """add tracked file"""
        if host_fl is None and local_fl is None:
            raise Exception("must pass host or local file")

        if host_fl is None:
            host_fl = local_fl
        elif local_fl is None:
            local_fl = host_fl

        local_fl = self.make_abs(local_fl)

        self.local_to_host.update([(local_fl, host_fl)])
        self.host_to_local.update([(host_fl, local_fl)])

    def del_tracker(self, host_fl=None, local_fl=None):
        if host_fl is None and local_fl is None:
            raise Exception("must pass host or local file")


        if host_fl is None:
            local_fl = self.make_abs(local_fl)
            host_fl = self.local_to_host[local_fl]
        elif local_fl is None:
            local_fl = self.host_to_local[host_fl]

        l = self.local_to_host.pop(local_fl, False)
        h = self.host_to_local.pop(host_fl, False)

        return bool(l and h)

    def make_abs(self, fl):
        if not os.path.isabs(fl):
            fl = os.path.join(self.pth, fl)
        return fl
