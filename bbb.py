"""
byebyebye - maintain two directories in sync (shallow).
"""
import argparse
import pickle
import os



PROJECT_EXT = '.fmap'
LAST_PROJECT = '.lastproj'
DEF_PROJECT = 'def'


def main():
    """high-level logic controller. verifies input and directs process"""

    args = init()

    project, file_mapping = resolve_project(args.project)

    if args.deploy and args.pull:
        print("cannot pull and deploy at the same time")
    elif args.add:
        new_file_mapping = track_file(args.add, args.trans, file_mapping)
        write_project(new_file_mapping, project)
    elif args.pull:
        sync_pull(file_mapping)
    elif args.deploy:
        sync_deploy(file_mapping)

def init():
    parser = argparse.ArgumentParser(description='Sync folders across network')

    parser.add_argument('-p', '--pull', action='store_true', default=False,
                        help='sync by pulling from remote directory')
    parser.add_argument('-d', '--deploy', action='store_true', default=False,
                        help='sync by pushing to remote directory')
    parser.add_argument('-a', '--add', type=str, metavar='f', action='store',
                        default=False, nargs="+", help='track files on remote')
    parser.add_argument('-t', '--trans', type=str, metavar='t',
                        default=False, action='store', nargs='*',
                        help='translated (local) file names for synced files' +
                        ' (optional, but only valid if -a/--add is also'      +
                        ' specified, in which case the file-list lengths'     +
                        ' must match')
    parser.add_argument('-j', '--project', type=str, metavar='j', const=False,
                        action='store', default=False, nargs='?',
                        help='project to operate on, if this is not ' +
                        'specified then the latest project will be used')
    args = parser.parse_args()
    print(args)
    return args

def resolve_project(project):
    transfer_mapping = dict()

    print("resolving project...")

    if not project:
        print("  project not passed...")
        if os.path.isfile(LAST_PROJECT):
            with open(LAST_PROJECT, 'r') as p:
                project = pickle.load(p)
            print("  found old project: " + project)
        else:
            project = DEF_PROJECT
            print("  could not find old project, using: " + project)
    else:
        print("  project passed: " + project)

    if os.path.isfile(project + PROJECT_EXT):
        with open(project + PROJECT_EXT, 'r') as f:
            transfer_mapping = pickle.load(f)

    if os.path.isfile(LAST_PROJECT):
        os.remove(LAST_PROJECT)
    with open(LAST_PROJECT, 'w') as p:
        pickle.dump(project, p)

    return project, transfer_mapping

def write_project(file_mapping, project):
    if os.path.isfile(project + PROJECT_EXT):
        os.remove(project + PROJECT_EXT)
    with open(project + PROJECT_EXT, 'w') as f:
        pickle.dump(file_mapping, f)

def track_file(file_list, trans_list, file_mapping):
    """
    add files to tracked list, optionally map remote file names to custom,
    local file names.
    """
    if trans_list:
        if len(trans_list) is not len(file_list):
            raise Exception('if file-name translations are given' +
                            'there must be a one-to-one mapping'  +
                            'to file names')
    else:
        trans_list = file_list

    print "adding tracked files:"
    print("\n".join(
        ["  mapping " + str(file_list[i]) + " --> " + str(trans_list[i])
         for i in range(len(file_list))]))

    file_mapping.update([(file_list[i], trans_list[i]) for i in
                         range(len(file_list))])

    return file_mapping

def sync_pull(project):
    """pull-specific logic"""
    print("pulling from remote")

def sync_deploy(project):
    """deploy-specific logic"""
    print("deploying to remote")

if __name__ == '__main__':
    main()
