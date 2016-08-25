"""
byebyebye - maintain two directories in sync (shallow).
"""
import argparse
import pickle
import os


def main():
    """high-level logic controller. verifies input and directs process"""

    args = init()

    project = resolve_project(args.project)

    if args.deploy and args.pull:
        print("cannot pull and deploy at the same time")
    elif args.add:
        track_file(args.add, args.trans, project)
    elif args.pull:
        sync_pull(project)
    elif args.deploy:
        sync_deploy(project)

def init():
    parser = argparse.ArgumentParser(description='Sync folders across network')

    parser.add_argument('-p', '--pull', action='store_true', default=False,
                        help='sync by pulling from remote directory')
    parser.add_argument('-d', '--deploy', action='store_true', default=False,
                        help='sync by pushing to remote directory')
    parser.add_argument('-a', '--add', type=str, metavar='f', action='store',
                        default=False, nargs="+", help='track files on remote')
    parser.add_argument('-t', '--trans', type=str, metavar='t',const=False,
                        default=False, action='store', nargs='*',
                        help='translated (local) file names for synced files' +
                        ' (optional, but only valid if -a/--add is also'      +
                        ' specified, in which case the file-list lengths'     +
                        ' must match')
    parser.add_argument('-j', '--project', type=str, metavar='j',
                        action='store', default=False, nargs='?',
                        help='project to operate on, if this is not ' +
                        'specified then the latest project will be used')
    args = parser.parse_args()
    print(args)
    return args

def resolve_project(project):
    transfer_mapping = dict()

    if not project:
        if os.path.isfile('.lastproj'):
            with open('.lastproj', 'r') as p:
                project = pickle.load(p)
        else:
            project = 'def'

    if os.path.isfile(project):
        with open(project + '.fmap', 'r') as f:
            transfer_mapping = pickle.load(f)
        os.remove('.lastproj')
        with open('.lastproj', 'w') as p:
            pickle.dump(project + '.fmap', '.lastproj')

    return transfer_mapping

def track_file(file_list, trans_list, project):
    """
    add files to tracked list, optionally map remote file names to custom,
    local file names.
    """
    print(file_list)
    if trans_list:
        print(trans_list)
    else:
        trans_list = file_list

def sync_pull(project):
    """pull-specific logic"""
    print("pulling from remote")

def sync_deploy(project):
    """deploy-specific logic"""
    print("deploying to remote")

if __name__ == '__main__':
    main()
