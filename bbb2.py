"""
byebyebye - maintain two directories in sync (shallow).
"""
import argparse
import pickle
import ftp_pull_test as ftp_pull
import proj
import os


BBB_HOME     = os.path.join(os.path.expanduser('~'), 'bbb')

DEF_PROJECT  = 'def'
PROJECT_EXT  = '.fmap'
LAST_PROJECT = os.path.join(BBB_HOME, '.lastproj')
PROJ_PROF    = os.path.join(BBB_HOME, '.projprof')

DEF_SPLIT_CHAR = "!"


def main():
    """high-level logic controller. verifies input and directs process"""

    args = init()

    if args.pull or args.deploy:
        if not args.host or not args.user:
            raise TypeError('must pass host -h and user -u')
        FTP = ftp_pull.ftp_init(args.host, args.user)
        if args.pull:
            for ftp_map in args.pull:
                host_fl, local_fl = split_ftp_map(ftp_map)
                ftp_pull.pull(host_fl, local_fl, FTP)
        elif args.deploy:
            for ftp_map in args.deploy:
                host_fl, local_fl = split_ftp_map(ftp_map)
                ftp_pull.deploy(host_fl, local_fl, FTP)
    else:
        project = resolve_project(args.project,
                                  args.host,
                                  args.user)
        if args.add:
            for ftp_map in args.add:
                host_fl, local_fl = split_ftp_map(ftp_map)
                project.add_tracker(host_fl=host_fl, local_fl=local_fl)
        elif args.delete:
            for ftp_map in args.delete:
                host_fl, local_fl = split_ftp_map(ftp_map)
                project.del_tracker(host_fl=host_fl, local_fl=local_fl)
        else:
            FTP = ftp_pull.ftp_init(project.host,
                                    project.user)
            if args.sync_pull:
                for host_fl, local_fl in project.host_to_local.items():
                    if os.path.isfile(local_fl):
                        os.remove(local_fl)
                    ftp_pull.pull(host_fl, local_fl, FTP)
            elif args.sync_deploy:
                for host_fl, local_fl in project.host_to_local.items():
                    ftp_pull.deploy(host_fl, local_fl, FTP)
        save_project(project)

def init():
    parser = argparse.ArgumentParser(description='Sync folders across network')

    mut_group_1 = parser.add_mutually_exclusive_group()

    mut_group_1.add_argument('-sp', '--sync-pull', action='store_true',
                        default=False,
                        help='sync all files in project' +
                        ' by pulling from the host')
    mut_group_1.add_argument('-sd', '--sync-deploy', action='store_true',
                        default=False,
                        help='sync all files in project by deploying' +
                        'to the host')
    mut_group_1.add_argument('-p', '--pull', action='store_true', default=False,
                        help='sync by pulling files from the host')
    mut_group_1.add_argument('-d', '--deploy', action='store_true', default=False,
                        help='sync by deploying files to the host')
    mut_group_1.add_argument('-a', '--add', type=str, metavar='f', action='store',
                        default=False, nargs="+",
                        help='add to files tracked in project')
    mut_group_1.add_argument('-del', '--delete', type=str, metavar='f', action='store',
                        default=False, nargs="+",
                        help='del from files tracked in project')
    parser.add_argument('-j', '--project', type=str, metavar='j', const=False,
                        action='store', default=False, nargs='?',
                        help='project to operate on, if this is not ' +
                        'specified then the latest project will be used')
    parser.add_argument('-r', '--host', '--remote', action='store', default=False,
                        help='host to connect and sync with')
    parser.add_argument('-u', '--user', action='store', default=False,
                        help='user to connect to the host as')
    args = parser.parse_args()
    print(args)
    return args

def split_ftp_map(ftp_map):
    split_list = ftp_map.split(DEF_SPLIT_CHAR)
    if len(split_list) is 0:
        raise TypeError('must pass file mapping')
    elif len(split_list) is 1:
        return split_list[0], split_list[0]
    elif len(split_list) is 2:
        return split_list[0], split_list[1]
    else:
        raise TypeError('too many files passed in mapping' +
                        '- ' + ftp_map)

def resolve_project(project, host, user):
    if not project:
        project = load_last_project()
        if host:
            project.host = host
        if user:
            project.user = user
    else:
        if project_exists(project):
            project = load_project(project)
            if host:
                project.host = host
            if user:
                project.user = user
        elif not host or not user:
            raise TypeError('must pass host -h and user -u to create project')
        else:
            project = proj.Proj(project, host, user)
            if not os.path.isdir(project.pth):
                os.mkdir(project.pth)

    return project

def load_last_project():
    if os.path.isfile(LAST_PROJECT):
        with open(LAST_PROJECT, 'r') as f:
            project_name = pickle.load(f)
            if os.path.isfile(os.path.join(BBB_HOME, project_name + ".proj")):
                with open(os.path.join(BBB_HOME, project_name + ".proj"), 'r') as f2:
                    ret_proj = pickle.load(f2)
                return ret_proj
    raise Exception('could not load last project')

def project_exists(project):
    project_path = os.path.join(BBB_HOME, project + ".proj")
    return os.path.isfile(project_path)

def load_project(project):
    project_path = os.path.join(BBB_HOME, project + ".proj")
    with open(project_path, 'r') as f:
        ret_proj = pickle.load(f)
    return ret_proj

def save_project(project):
    if not os.path.isdir(BBB_HOME):
        os.mkdir(BBB_HOME)
    if os.path.isfile(os.path.join(BBB_HOME, project.name + ".proj")):
        os.remove(os.path.join(BBB_HOME, project.name + ".proj"))
    with open(os.path.join(BBB_HOME, project.name + ".proj"), 'w') as f:
        pickle.dump(project, f)
    if os.path.isfile(LAST_PROJECT):
        os.remove(LAST_PROJECT)
    with open(LAST_PROJECT, 'w') as f:
        pickle.dump(project.name, f)

if __name__ == '__main__':
    main()
