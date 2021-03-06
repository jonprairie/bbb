"""
byebyebye - maintain two directories in sync (shallow).
TODO: clean up too-general exceptions
"""
import argparse
import shutil
import filecmp
import difflib
import pickle
import sys
import os
import ftp_wrap
import proj

# try importing module for colored terminal output
try:
    import colorama
    colorama.init()
    colors_available = True
except ImportError:
    colors_available = False

# BBB_HOME     = os.path.join(os.path.expanduser('~'), 'bbb')
BBB_HOME     = os.path.join(os.environ['USERPROFILE'], 'bbb')

DEF_PROJECT  = 'def'
PROJECT_EXT  = '.proj'
LAST_PROJECT = os.path.join(BBB_HOME, '.lastproj')
LAST_CONN    = os.path.join(BBB_HOME, '.lastconn')
BKUP_EXT     = 'bkup'

DEF_SPLIT_CHAR = "!"


def main():
    """high-level logic controller. calls init to parse command-line input, then
    calls the returned args.func function on the parsed arguments"""

    args = init()
    args.func(args)


def sync_pull_control(args):
    try:
        project = load_last_project()
        FTP = ftp_wrap.init(project.host, project.user)
        sync_pull(project, FTP)
    except Exception as e:
        print("error: could not pull project")


def sync_pull_list_control(args):
    try:
        project = load_last_project()
        k = list(project.host_to_local.keys())
        pull_list = []

        for n in range(len(k)):
            pull_list.append((
                n,
                k[n],
                project.host_to_local[k[n]]
            ))

        print("\nfile links in project %s:" % project.name)

        for line in pull_list:
            print("  %d: %s --> %s" % line)

        selection = input(
            "\ninput comma-separated list of integer keys to be pulled from host:\n--> "
        )

        sel_list = list(
            filter(
                lambda x: x and int(x) not in k,
                ",".join(selection.split(" ")).split(",")
            )
        )

        chosen_list = list(map(
            lambda x: pull_list[int(x)],
            sel_list
        ))

        yes_no_str = "\nplease confirm, pull the following files from host and overwrite local versions?" 
        yes_no_list = ["\n  %d: %s --> %s" % (n, h, l) for n, h, l in chosen_list]

        if yes_no(yes_no_str + "".join(yes_no_list) + "\n--> "):
            FTP = ftp_wrap.init(project.host, project.user)
            for _, host_fl, local_fl in chosen_list:
                pass
                pull_from_host(host_fl, local_fl, FTP)
                bkup_fl(local_fl, get_bkup_path(project, host_fl))
        else:
            print("\ncancelling...")
    except Exception as e:
        print("error: could not deploy project")
        print(str(e))


def sync_depl_control(args):
    try:
        project = load_last_project()
        FTP = ftp_wrap.init(project.host, project.user)
        sync_deploy(project, FTP, args.force)
    except Exception as e:
        print("error: could not deploy project")


def sync_depl_list_control(args):
    try:
        project = load_last_project()
        k = list(project.host_to_local.keys())
        depl_list = []

        for n in range(len(k)):
            depl_list.append((
                n,
                k[n],
                project.host_to_local[k[n]]
            ))

        print("\nfile links in project %s:" % project.name)

        for line in depl_list:
            print("  %d: %s <-- %s" % line)

        selection = input(
            "\ninput comma-separated list of integer keys to be deployed to host:\n--> "
        )

        sel_list = list(
            filter(
                lambda x: x and int(x) not in k,
                ",".join(selection.split(" ")).split(",")
            )
        )

        chosen_list = list(map(
            lambda x: depl_list[int(x)],
            sel_list
        ))

        yes_no_str = "\nplease confirm, deploy the following files to host and overwrite remote versions?" 
        yes_no_list = ["\n  %d: %s <-- %s" % (n, h, l) for n, h, l in chosen_list]

        if yes_no(yes_no_str + "".join(yes_no_list) + "\n--> "):
            FTP = ftp_wrap.init(project.host, project.user)
            for _, host_fl, local_fl in chosen_list:
                ftp_wrap.deploy(host_fl, local_fl, FTP)
                bkup_fl(local_fl, get_bkup_path(project, host_fl))
        else:
            print("\ncancelling...")
    except Exception as e:
        print("error: could not deploy project")
        print(str(e))


def sync_stgd_control(args):
    # TODO: extract color formatting logic
    try:
        project = load_last_project()
    except Exception as e:
        print(e)
        print("error:could not load project")
        sys.exit(1)

    chg_fls, ident_fls = test_proj_for_changes(project)

    print("\n"+project.name)
    for fl in chg_fls:
        chg_str = "changes detected in: " + fl
        if colors_available:
            chg_str = colorama.Fore.GREEN + chg_str + colorama.Style.RESET_ALL
        chg_str = "  " + chg_str
        print(chg_str)
        if args.verbose:
            bkup_fl = get_bkup_path(project, project.local_to_host[fl])
            diff = diff_files(bkup_fl, fl)
            if colors_available:
                diff_colors = []
                for line in diff:
                    if len(line) >= 3 and line[0:3] in ['---', '***']:
                        line = colorama.Style.BRIGHT + colorama.Fore.BLACK + line + colorama.Style.RESET_ALL
                    elif line[0] == '+' and (len(line) == 1 or line[1] == ' '):
                        line = colorama.Fore.GREEN + line + colorama.Style.RESET_ALL
                    elif line[0] == '-' and (len(line) == 1 or line[1] == ' '):
                        line = colorama.Fore.RED + line + colorama.Style.RESET_ALL
                    elif line[0] == '!' and (len(line) == 1 or line[1] == ' '):
                        # line = colorama.Style.BRIGHT + colorama.Fore.BLUE + line + colorama.Style.RESET_ALL
                        line = colorama.Fore.MAGENTA + line + colorama.Style.RESET_ALL
                    diff_colors.append(line)
                diff = diff_colors
            print("".join(list(map(lambda x: "     |"+x, diff))), end="")
    for fl in ident_fls:
        ident_str = "no changes found in : " + fl
        if colors_available:
            ident_str = colorama.Fore.RED + ident_str + colorama.Style.RESET_ALL
        ident_str = "  " + ident_str
        print(ident_str)

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
    return os.path.join(BBB_HOME, project.name, BKUP_EXT)

def get_project_relative_path(project, fl_path, path_stack=list()[:]):
    if os.path.split(fl_path)[0] == "":
        return fl_path
    elif os.path.splitdrive(fl_path)[1] in ["", "/"]:
        return os.path.join(*path_stack)
    elif os.path.split(fl_path)[1] == project.name:
        return os.path.join(*path_stack)
    else:
        root, leaf = os.path.split(fl_path)
        fl_path = root
        path_stack.append(leaf)
        return get_project_relative_path(
            project,
            fl_path,
            path_stack=path_stack
        )

def get_bkup_path(project, fl):
    fl_path = get_project_relative_path(project, fl)
    return os.path.join(get_bkup_home(project), fl_path + "." + BKUP_EXT)

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
    "TODO: should reimplement this using test_proj_for_changes()"
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

def test_proj_for_changes(project):
    changed_files = []
    ident_files = []
    for host_fl, local_fl in project.host_to_local.items():
        bkup_fl_path = get_bkup_path(project, host_fl)
        if os.path.isfile(bkup_fl_path):
            if not filecmp.cmp(local_fl, bkup_fl_path):
                changed_files.append(local_fl)
            else:
                ident_files.append(local_fl)
        else:
            changed_files.append(local_fl)
    return changed_files, ident_files

def diff_files(file_1, file_2):
    with open(file_1, encoding='utf-8') as f_1, \
         open(file_2, encoding='utf-8') as f_2:
        diff_list = list(
            difflib.context_diff(
                f_1.readlines(),
                f_2.readlines(),
                fromfile=os.path.split(file_1)[1],
                tofile=os.path.split(file_2)[1]
            )
        )
    return diff_list


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

    verboseable = argparse.ArgumentParser(add_help=False)
    verboseable.add_argument(
        '-v', '--verbose', action='store_true',
        help='print verbose output'
    )

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
    sync_pull = sync_sub.add_parser(
        'pull',
        parents=[forceable],
        help="pull all files tracked in current project from host"
    )
    sync_pull_list = sync_sub.add_parser(
        'selp',
        parents=[forceable],
        help="select list of files to pull from host"
    )
    sync_deploy = sync_sub.add_parser(
        'deploy',
        parents=[forceable],
        help="deploy changed files tracked in current project to host"
    )
    sync_deploy_list = sync_sub.add_parser(
        'seld',
        parents=[forceable],
        help="select list of files to deploy to host"
    )
    sync_staged = sync_sub.add_parser(
        'staged', parents=[verboseable],
        help="list files that have unsynchronized changes"
    )

    # create parser for "ftp" command
    # not currently working, needs to be tied in
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

    # create parser for "conf" command
    conf_parser = subparsers.add_parser('conf', help='manage configuration')
    conf_sub = conf_parser.add_subparsers(title="actions")
    conf_conn = conf_sub.add_parser('conn', help='add new connection')
    conf_conn.add_argument('user', type=str, metavar='user', action='store',
                           nargs=1, help='user to connect as')
    conf_conn.add_argument('host', type=str, metavar='host', action='store',
                           nargs=1, help='host to connect with')

    sync_pull.set_defaults(func=sync_pull_control)
    sync_pull_list.set_defaults(func=sync_pull_list_control)
    sync_deploy.set_defaults(func=sync_depl_control)
    sync_deploy_list.set_defaults(func=sync_depl_list_control)
    sync_staged.set_defaults(func=sync_stgd_control)

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
