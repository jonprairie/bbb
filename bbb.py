"""
byebyebye - sync files between two folders, one of which can
be remote.
"""
import argparse
import ftp_pull


def main():
    args = init()
    print(args)

    try:
        validate(args)
        channel(args)
    except Exception as e:
        print("call to bbb not valid: " + str(e))

def init():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--add", type=str,
                        nargs="+", metavar="f", default=False,
                        help="add file to track list")
    parser.add_argument("-r", "--retr", type=str,
                        nargs="+", metavar="r", default=False,
                        help="files to retrieve (files" +
                        " are not tracked)")
    parser.add_argument("-t", "--trans", type=str,
                        nargs="+", metavar="t", default=False,
                        help="local, translated file names" +
                        ", used to rename remote files when" +
                        " retrieved.")
    parser.add_argument("-d", "--depl", type=str,
                        nargs="+", metavar="d", default=False,
                        help="files to be deployed on the host")
    return parser.parse_args()

def validate(args):
    if args.retr or args.depl:
        if args.trans:
            if args.retr and len(args.trans) is not len(args.retr):
                if args.depl and len(args.trans) is not len(args.depl):
                    raise Exception("if translated files"   +
                                    " are passed in, there" +
                                    " must be a one-to-one" +
                                    " correspondence to "   +
                                    "retrieved files")
        else:
            if args.retr:
                args.trans = args.retr
            elif args.depl:
                args.trans = args.depl

def channel(args):
    if args.retr:
        files = sync_pull(args.retr, args.trans)
    elif args.depl:
        files = sync_deploy(args.depl, args.trans)
    #    for f in files:
    #        print(f)

def sync_pull(retr, trans):
    FTP = ftp_pull.ftp_init()
    print("retrieving files:")

    ret_list = [
        ftp_pull.pull(f, t, FTP)
        for f, t in zip(retr, trans)
    ]

    return ret_list

def sync_deploy(depl, trans):
    FTP = ftp_pull.ftp_init()
    print("deploying files:")

    ret_list = [
        ftp_pull.deploy(f, t, FTP)
        for f, t in zip(depl, trans)
    ]

    return ret_list

if __name__ == '__main__':
    main()
