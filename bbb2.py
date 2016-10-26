"""
byebyebye - maintain two directories in sync (shallow).
"""
import argparse
import shutil
import filecmp
import pickle
import ftp_wrap
import proj
import os


BBB_HOME     = os.path.join(os.path.expanduser('~'), 'bbb')

DEF_PROJECT  = 'def'
PROJECT_EXT  = '.proj'
LAST_PROJECT = os.path.join(BBB_HOME, '.lastproj')
LAST_CONN    = os.path.join(BBB_HOME, '.lastconn')
BKUP_EXT     = 'bkup'

DEF_SPLIT_CHAR = "!"


def main():
    """high-level logic controller. calls init to parse input, then
    calls the returned args.func function on the parsed arguments"""

    args = init()
    print(args)
    args.func(args)

def sync_pull_control(args):
    try:
        project = load_last_project()
        FTP = ftp_wrap.init(project.host, project.user)
        sync_pull(project, FTP)
    except Exception as e:
        print("error: could not pull project")

def sync_depl_control(args):
    try:
        project = load_last_project()
        FTP = ftp_wrap.init(project.host, project.user)
        sync_deploy(project, FTP, args.force)
    except Exception as e:
        print("error: could not deploy project")

def proj_new_control(args):
    try:
        project = create_new_project(args.project[0])
        switch_project(project)
        print("\ncreated new project: " + project.name)
    except Exception as e:
        print("error: could not create project")

def proj_del_control(args):
    project = args.project[0]
    if yes_no("are you sure you want to delete this project?"):
        print('\ndeleting %s' % project)
        try:
            delete_proj_src(project)
            delete_project(project)
        except Exception as e:
            print("error: could not delete project")

def proj_ren_control(args):
    project = args.project[0]
    new_proj = args.project[1]
    try:
        if yes_no("are you sure you want to rename this project?") \
                and project_exists(project):
            print('\nrenaming %s to %s' % (project, new_proj))
            proj_obj = load_project(project)
            old_proj_path = proj_obj.pth
            proj_obj.change_name(new_proj)
            proj_obj.move_proj(None)
            save_project(proj_obj)
            shutil.move(old_proj_path, proj_obj.pth)
            delete_project(project)
        else:
            raise Exception("project doesn't exist")
    except Exception as e:
        print("error: could not rename project")

def proj_swi_control(args):
    if project_exists(args.project[0]):
        project = load_project(args.project[0])
        switch_project(project)
        print("\nswitched current project to: " + project.name)
    else:
        print("error: could not load " +
              args.project[0] + ", project does not exist")

def proj_add_control(args):
    try:
        project = load_last_project()
        print("\n" + project.name)
        init_control_sw = None
        FTP = None
        for file_map in args.file_mappings:
            host_fl, local_fl = split_ftp_map(file_map)
            project.add_tracker(host_fl=host_fl, local_fl=local_fl)
            local_fl_abs = project.host_to_local[host_fl]
            print("  tracking: " + host_fl + " --> " + local_fl)
            if not os.path.isfile(local_fl_abs):
                if init_control_sw is "a":
                    FTP = connect_and_pull(host_fl, local_fl_abs, FTP)
                elif init_control_sw is not "v":
                    while init_control_sw not in ["y", "n", "a", "v"]:
                        inp = input(os.path.basename(local_fl_abs) +
                                    " does not exist locally,\ndownload?" +
                                    "(y)es, (n)o, (a)lways, ne(v)er\n==> ")
                        init_control_sw = inp
                    if init_control_sw in ["y", "a"]:
                        FTP = connect_and_pull(host_fl, local_fl_abs, FTP)
        save_project(project)
    except Exception as e:
        print("error: could not load project")

def connect_and_pull(host_fl, local_fl, FTP):
    if FTP is None:
        user, host = load_last_conn()
        FTP = ftp_wrap.init(host, user)
    pull_from_host(host_fl, local_fl, FTP)
    return FTP

def proj_rem_control(args):
    try:
        project = load_last_project()
        print("\n" + project.name)
        for file_map in args.file_mappings:
            host_fl, local_fl = split_ftp_map(file_map)
            project.del_tracker(host_fl=host_fl, local_fl=local_fl)
            print("  untracking: " + host_fl + " --> " + local_fl)
        save_project(project)
    except Exception as e:
        print("error: could not load project")
        
def proj_list_control(args):
    try:
        project = load_last_project()
        print("\n" + project.name)
        for fl in project.host_to_local.keys():
            print("  " + fl + " --> " + project.host_to_local[fl])
    except Exception as e:
        print("error: could not load project")

def conf_conn_control(args):
    conn_dict = dict(host=args.host[0], user=args.user[0])
    if os.path.isfile(LAST_CONN):
        os.remove(LAST_CONN)
    with open(LAST_CONN, 'wb') as f:
        pickle.dump(conn_dict, f)
    print("\ndefault connection - host: " + conn_dict["host"] +
            " - user: " + conn_dict["user"])

def load_last_conn():
    with open(LAST_CONN, 'rb') as f:
        ret_conn = pickle.load(f)
        return ret_conn["user"], ret_conn["host"]

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

def create_new_project(name):
    if not project_exists(name):
        user, host = load_last_conn()
        project = proj.Proj(name, host, user)
        if not os.path.isdir(project.pth):
            build_dir(project.pth)
        if not os.path.isdir(get_bkup_home(project)):
            build_dir(get_bkup_home(project))
        save_project(project)
        return project
    else:
        raise Exception()

def load_last_project():
    if os.path.isfile(LAST_PROJECT):
        with open(LAST_PROJECT, 'rb') as f:
            project_name = pickle.load(f)
            if os.path.isfile(os.path.join(BBB_HOME, project_name + PROJECT_EXT)):
                with open(os.path.join(BBB_HOME, project_name + PROJECT_EXT), 'rb') as f2:
                    ret_proj = pickle.load(f2)
                return ret_proj
    raise Exception('could not load last project')

def switch_project(project):
    if os.path.isfile(LAST_PROJECT):
        os.remove(LAST_PROJECT)
    with open(LAST_PROJECT, 'wb') as f:
        pickle.dump(project.name, f)

def project_exists(project):
    return os.path.isfile(get_proj_path(project))

def delete_project(project):
    """deletes files project-related files, does not delete
    src directory or files"""
    if project_exists(project):
        os.remove(get_proj_path(project))
        shutil.rmtree(get_proj_dir_path(project))

def delete_proj_src(project):
    """deletes src directory and files"""
    if project_exists(project):
        shutil.rmtree(get_proj_src_dir_path(project))

def load_project(project):
    with open(get_proj_path(project), 'rb') as f:
        ret_proj = pickle.load(f)
    return ret_proj

def save_project(project):
    # refactor to use proj_exists and get_proj_path
    if not os.path.isdir(BBB_HOME):
        build_dir(BBB_HOME)
    if os.path.isfile(os.path.join(BBB_HOME, project.name + PROJECT_EXT)):
        os.remove(os.path.join(BBB_HOME, project.name + PROJECT_EXT))
    with open(os.path.join(BBB_HOME, project.name + PROJECT_EXT), 'wb') as f:
        pickle.dump(project, f)

def get_proj_path(project):
    return os.path.join(BBB_HOME, project + PROJECT_EXT)

def get_proj_dir_path(project):
    return os.path.join(BBB_HOME, project)

def get_proj_src_dir_path(project):
    proj = load_project(project)
    return proj.pth

def get_bkup_home(project):
    return os.path.join(BBB_HOME, project.name,
                        BKUP_EXT)
    
def get_bkup_path(project, fl):
    return os.path.join(get_bkup_home(project), fl + "." +
                        BKUP_EXT)

def bkup_fl(source_fl, target_fl):
    if not os.path.isdir(os.path.dirname(target_fl)):
        build_dir(os.path.dirname(target_fl))
    shutil.copy2(source_fl, target_fl)

def build_dir(dr):
    if not os.path.isdir(os.path.dirname(dr)):
        build_dir(os.path.dirname(dr))
    os.mkdir(dr)

def sync_pull(project, FTP):
    print("syncing files...")
    for host_fl, local_fl in project.host_to_local.items():
        pull_from_host(host_fl, local_fl, FTP)
        bkup_fl(local_fl, get_bkup_path(project, host_fl))

def sync_deploy(project, FTP, force):
    print("syncing files...")
    for host_fl, local_fl in project.host_to_local.items():
        bkup_fl_path = get_bkup_path(project, host_fl)
        if os.path.isfile(bkup_fl_path):
            if force or not filecmp.cmp(local_fl, bkup_fl_path):
                ftp_wrap.deploy(host_fl, local_fl, FTP)
                bkup_fl(local_fl, get_bkup_path(project, host_fl))
            else:
                print("  no changes to " + local_fl)
        else:
            ftp_wrap.deploy(host_fl, local_fl, FTP)
            bkup_fl(local_fl, get_bkup_path(project, host_fl))

def pull_from_host(host_fl, local_fl, FTP):
    if os.path.isfile(local_fl):
        os.remove(local_fl)
    ftp_wrap.pull(host_fl, local_fl, FTP)

def yes_no(q):
    ans = ""
    while ans.upper() not in ['YES', 'Y', 'NO', 'N']:
        ans = input(q + " [yes, y, no, n]: ")
    return ans.upper() in ['YES', 'Y']

def init():
    parser = argparse.ArgumentParser(
        description='Sync projects across network'
    )
    subparsers = parser.add_subparsers()

    forceable = argparse.ArgumentParser(add_help=False)
    forceable.add_argument('-f', '--force', action='store_true',
                           help='force action and ignore warnings')

    fm_parser = argparse.ArgumentParser(add_help=False)
    fm_parser.add_argument('file_mappings', type=str, metavar='file_map',
                           action='store', nargs="+",
                           help='file mapping, in the format of: ' +
                           'host_file' + DEF_SPLIT_CHAR + 'local_file')

    proj_name_parser = argparse.ArgumentParser(add_help=False)
    proj_name_parser.add_argument('project', type=str, metavar='project',
                                  action='store', nargs="+",
                                  help='project name')

    # create parser for "sync" command
    sync_parser = subparsers.add_parser('sync', help='sync files in project')
    sync_sub = sync_parser.add_subparsers(title="actions")
    sync_pull = sync_sub.add_parser('pull', parents=[forceable],
                                    help='''pull files tracked in current
                                            project from the host''')
    sync_deploy = sync_sub.add_parser('deploy', parents=[forceable],
                                      help='''deploy files tracked in current
                                              project to the host''')
                                    
    # create parser for "ftp" command
    ftp_parser = subparsers.add_parser('ftp', help='ftp files to/from host')
    ftp_sub = ftp_parser.add_subparsers(title="actions")
    ftp_pull = ftp_sub.add_parser('pull', parents=[fm_parser, forceable],
                                  help='pull files from host')
    ftp_deploy = ftp_sub.add_parser('deploy', parents=[fm_parser, forceable],
                                    help='deploy files to host')

    # create parser for "proj" command
    proj_parser = subparsers.add_parser('proj', help='manage projects')
    proj_sub = proj_parser.add_subparsers(title="actions")
    proj_new = proj_sub.add_parser('new', parents=[proj_name_parser],
                                   help='create new project')
    proj_del = proj_sub.add_parser('del', parents=[proj_name_parser],
                                   help='delete project')
    proj_ren = proj_sub.add_parser('ren', parents=[proj_name_parser],
                                   help='rename project')
    proj_swi = proj_sub.add_parser('switch', parents=[proj_name_parser],
                                   help='switch projects')
    proj_add = proj_sub.add_parser('add', parents=[fm_parser],
                                   help='add file-mapping to current project')
    proj_rem = proj_sub.add_parser('rem', parents=[fm_parser],
                                   help='remove file-mapping from current project')
    proj_list = proj_sub.add_parser('list', help='list file mappings in ' +
                                    'current project')

    #create parser for "conf" command
    conf_parser = subparsers.add_parser('conf', help='manage configuration')
    conf_sub = conf_parser.add_subparsers(title="actions")
    conf_conn = conf_sub.add_parser('conn', help='add new connection')
    conf_conn.add_argument('user', type=str, metavar='user', action='store',
                           nargs=1, help='user to connect as')
    conf_conn.add_argument('host', type=str, metavar='host', action='store',
                           nargs=1, help='host to connect with')

    sync_pull.set_defaults(func=sync_pull_control)
    sync_deploy.set_defaults(func=sync_depl_control)

    proj_new.set_defaults(func=proj_new_control)
    proj_del.set_defaults(func=proj_del_control)
    proj_ren.set_defaults(func=proj_ren_control)
    proj_swi.set_defaults(func=proj_swi_control)
    proj_add.set_defaults(func=proj_add_control)
    proj_rem.set_defaults(func=proj_rem_control)
    proj_list.set_defaults(func=proj_list_control)

    conf_conn.set_defaults(func=conf_conn_control)

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    main()
