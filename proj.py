"""
representation of a project to be synchronized
"""
import os


class Proj:
    def __init__(self, name, host=None, user=None, pth=None, auto_load=False):
        self.name = name

        # orig_path is the original path passed into proj,
        # pth is the qualified path to save all tracked, local files
        self.orig_path = pth
        self.pth = self.qual_path(pth)

        self.auto_load = auto_load

        self.user = user
        self.host = host

        self.local_to_host = dict()
        self.host_to_local = dict()

    def move_proj(self, pth):
        new_pth = self.qual_path(pth)
        new_l_to_h = {
            os.path.join(
                new_pth,
                self.extr_orig_file_name(l_fl)
            ): h_fl
            for l_fl, h_fl in self.local_to_host.items()
        }
        new_h_to_l = {
            h_fl: l_fl for l_fl, h_fl in new_l_to_h.items()
        }
        self.local_to_host = new_l_to_h
        self.host_to_local = new_h_to_l

    def extr_orig_file_name(self, fl_pth):
        if fl_pth.startswith(self.pth):
            old_pth = os.path.join(self.pth, '')
            orig_file = fl_pth[len(old_pth):]
            return orig_file
        else:
            raise ValueError(
                "%s isn't qualified by %s" % (fl_pth, self.pth)
            )



    def qual_path(self, pth):
        if pth is not None and not os.path.isabs(pth):
            pth = os.path.abspath(pth)
        elif pth is None:
            pth = os.path.abspath(self.name)
        return pth   

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
