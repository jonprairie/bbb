import ftplib
import getpass
import sys
import os
import io


DEFAULT_HOST = 'localhost'
DEFAULT_USER = getpass.getuser()


def pull(fl, t_fl, FTP):
    """
    retrieves fl, a remote file from the host
    and saves it locally to t_fl.

    note: t_fl is deleted if it already exists!
    """

    print("  " + fl + " --> " + t_fl)          
    if os.path.isfile(t_fl):
        print("    " + t_fl + " already exists, deleting...")
        os.remove(t_fl)

    f = open(t_fl, 'w')
    def write_line(l):
        f.write(l + "\n")

    try:
        ret_fl = FTP.retrlines('RETR ' + fl, write_line)
    except Exception as e:
        FTP.quit()
        print("  failed to retrieve file: " + fl)
        raise e
    finally:
        f.close()

    return ret_fl

def deploy(fl, t_fl, FTP):
    """
    deploys t_fl, a local file, to the host
    as fl
    """
    try:
        print("  " + fl + " <-- " + t_fl)
        with open(t_fl, 'rb') as f:
            FTP.storlines('STOR ' + fl, f)
    except Exception as e:
        FTP.quit()
        print("  failed to deploy file: " + t_fl)
        raise e

def ftp_init(host=DEFAULT_HOST, user=DEFAULT_USER):
    FTP = ftplib.FTP(host)
    # print(FTP.getwelcome())
    print("connecting to " + host +
          " as " + user + "...")

    password = getpass.getpass() 

    try:
        FTP.login(user, password)
        print("logon successful")
    except Exception as e:
        FTP.quit()
        raise Exception("ftp logon failed: " + str(e))

    return FTP
