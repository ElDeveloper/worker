#!/usr/bin/env python
from __future__ import print_function

__author__ = "Yoshiki Vazquez-Baeza"
__credits__ = ["Yoshiki Vazquez Baeza"]
__copyright__ = "Copyright 2013, Worker"
__license__ = "GPL"
__version__ = "1.0.0-dev"
__maintainer__ = "Yoshiki Vazquez-Baeza"
__email__ = "yoshiki89@gmail.com"
__status__ = "Development"


from urllib import urlopen
from site import addsitedir
from sys import argv, stderr
from json import load as load_json
from subprocess import check_output
from shutil import copytree, rmtree
from re import compile as re_compile
from os import chdir, getcwd, makedirs
from os.path import split as path_split
from datetime import datetime, timedelta
from subprocess import Popen, PIPE, STDOUT
from os.path import abspath, dirname, join, basename, splitext, exists

# https://api.github.com/repos/qiime/emperor/pulls
# curl -i https://api.github.com/repos/qiime/emperor | less -S

# repository that we want to be pulling from
GITHUB_URL = "https://api.github.com/repos/qiime/emperor/pulls"

# HTML formatting strings for the index.html files for each pull request
GENERIC_INDEX = """<!DOCTYPE html>
<html>
<body>
<h1>Examples built from <a href="%s">%s</a></h1>
%s
</body>
</html>"""
GENERIC_LINK = """<br><a href="%s">%s</a>
"""

# Taken from matplotlib's tools/github_stats.py
def parse_link_header(headers):
    link_s = headers.get('link', '')
    urls = re_compile(r'<(.+?)>').findall(link_s)
    rels = re_compile(r'rel=[\'"](\w+)[\'"]').findall(link_s)
    d = {}
    for rel,url in zip(rels, urls):
        d[rel] = url
    return d

# Taken from matplotlibs tools/github_stats.py
def get_paged_request(url):
    """get a full list, handling APIv3's paging"""
    results = []
    while url:
        print("fetching %s" % url)
        f = urlopen(url)
        results.extend(load_json(f))
        links = parse_link_header(f.headers)
        url = links.get('next')
    return results

# taken from QIIME qiime/util.py
def qiime_system_call(cmd, shell=True):
    """Call cmd and return (stdout, stderr, return_value).

    cmd can be either a string containing the command to be run, or a sequence
    of strings that are the tokens of the command.

    Please see Python's subprocess.Popen for a description of the shell
    parameter and how cmd is interpreted differently based on its value.
    """
    proc = Popen(cmd, shell=shell, universal_newlines=True, stdout=PIPE,
        stderr=PIPE)
    # communicate pulls all stdout/stderr from the PIPEs to 
    # avoid blocking -- don't remove this line!
    stdout, stderr = proc.communicate()
    return_value = proc.returncode
    return stdout, stderr, return_value

def run_script_usage_examples(script_path, output_dir):
    """Run the script usage tests for a path with scripts

    Inputs:
    script_path: path where the scripts that will be executed can be found
    output_dir: path where the scripts will be executed, these path must include
    folders for the inputs of the script_usage_examples of the scripts in
    script_path

    Heavily based on QIIME's/QCLI's script usage testing"""

    # without these two assertions being true the results could be unexpected
    assert exists(script_path), "The script path does not exist"
    assert exists(output_dir), "The output directory has to exist"

    original_dir = getcwd()
    chdir(output_dir)

    string_to_write = GENERIC_INDEX
    links = []

    # retrieve multi-purpose variables
    script_name = splitext(basename(script_path))[0]
    script_dir = dirname(abspath(script_path))

    # add the folder where the scripts are located
    addsitedir(script_dir)
    test_data_dir = join(dirname(script_dir), 'tests/scripts_test_data/%s/' %
        script_name)

    # import the script of interest
    script = __import__(script_name)

    # retrieve the dictionary of usage examples, where the actual command is the
    # third element in the tuple, remember that %prog should be replaced by the
    # name of the script that needs to be tested right now
    usage_examples = script.script_info['script_usage']

    # copying a full tree in python is complicated when you don't care about
    # overwritting the contents of existing folders hence the system call
    o, e, _ = qiime_system_call('cp -Rf "%s" "%s"' % (test_data_dir,output_dir))

    # go to the script directory and run the usage examples
    chdir(script_name)

    for example in usage_examples:
        # %prog is the keyword in the scripts replace for the script name
        cmd = example[2].replace('%prog',script_name+'.py')
        o, e, _ = qiime_system_call(cmd)

        # we should get the output name for the folder
        name = cmd.split('-o')[1].split(' ')[1]
        links.append(GENERIC_LINK % (join(name, 'index.html'), name))
        
        print('Deleting: %s' % name)
        try:
            rmtree(name)
        except:
            pass

        #raw_input('This folder has been delated %s' % name)
        o, e, r = qiime_system_call(cmd)
        print("Executing: " + cmd)
        if r != 0: print(o, e)

    fd = open('index.html', 'w')
    if basename(output_dir) == 'master':
        fd.write(GENERIC_INDEX%("https://github.com/qiime/emperor/tree/master",
            basename(output_dir), ''.join(links)))
    else:
        fd.write(GENERIC_INDEX%("https://github.com/qiime/emperor/pull/"+\
            basename(output_dir).split('_')[1], basename(output_dir), ''.join(
            links)))
    fd.close()

    chdir(original_dir)


def branch_problem(message, git_string, pull_number):
    """Recover after a problem in a PullRequest branch

    message: string describing the problem that originated this purge
    git_string: string prefix of the git call for git commands to be executed
    pull_number: string with the number of the issue in GitHub.com

    if something went wrong with the system call then clean all unusable
    files, reset the repository to the latest head and force a checkout
    of the master branch in the current repository so any of the other
    pull requests that are open are not affected by this problem"""

    print(message)
    print('Cleaning the repo ...')

    # clean any extraneous files that are laying around
    cmd = '%s clean -xdf' % git_string
    o, e, r = qiime_system_call(cmd)
    if r != 0: print('Fatal, could not clean the repository.')
    exit(1)

    # undo all the changes that could have been generated
    cmd = '%s reset --hard HEAD *' % git_string
    o, e, r = qiime_system_call(cmd)
    if r != 0: print('Fatal, could not reset to the current HEAD.')
    exit(1)

    # force back to be at the master branch
    cmd = '%s checkout -f master' % git_string
    o, e, r = qiime_system_call(cmd)
    if r != 0: print('Fatal, could not force back to master.')
    exit(1)

    # delete the current branch
    cmd = '%s branch -D pull_%s' % (git_string, pull_number)
    o, e, r = qiime_system_call(cmd)
    if r != 0: print('Could not delete the branch.')


if __name__ == "__main__":

    # a la viva mexico! (read with an american accent)
    try:
        emperor_path = argv[1]
    except IndexError:
        emperor_path = '/home/yova1074/emperor/'
    try:
        master_path = argv[2]
    except IndexError:
        master_path = '/var/www/html/master'

    # this string is annoyingly re-used in every git command call
    GIT_STRING = 'git --git-dir=%s/.git ' % emperor_path
    PULL = '%s pull git://github.com/qiime/emperor.git master' % GIT_STRING
    e, o, r = qiime_system_call(PULL)

    # we must be able to pull from master, if this is not possible exit
    if r != 0:
        print('Could not pull from master, not continuing.')
        print(o, e)
        exit(1)

    # if we were able to update master build the script_path and run the 
    script_path = join(emperor_path, 'scripts/make_emperor.py')
    run_script_usage_examples(script_path, master_path)

    # fetch all the open pull requests
    try:
        results = get_paged_request(GITHUB_URL)
    except IOError:
        print('Could not establish a connection', file=stderr)

    if len(results) == 0:
        print('There are no active pull requests to deploy')
        exit(0)

    # if we found active pull requests then deploy them
    for result in results:
        print('Active pull request "pull_%s"' % result['number'])
        print('URL: %s' % result['head']['repo']['git_url'])
        print('Branch name: %s' % result['head']['ref'])

        deploying_folder = join(dirname(master_path), 'pull_'+str(
            result['number']))
        print('Folder where the pull request will be deployed: ',
            deploying_folder)

        chdir(emperor_path)

        # create a new branch where this open pull request will live
        cmd = '%s checkout -b pull_%s' % (GIT_STRING, result['number'])
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            branch_problem('could not checkout a new branch')
            continue

        # pull stuff from the branch in question
        cmd = '%s pull %s %s' % (GIT_STRING, result['head']['repo']['git_url'],
            result['head']['ref'])
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            branch_problem('could not pull down the custom branch')
            continue

        # once we pull whether or not it's right i. e. no conflicts, remove the
        # previous folder to ensure there are no confusions with the data
        try:
            rmtree(deploying_folder)
        except OSError:
            pass
        finally:
            makedirs(deploying_folder)

        # if nothing went wrong, run the script usage examples that will finally
        # let you see the rendered examples for this pull request
        run_script_usage_examples(script_path, deploying_folder)

        # go back to master so everything is kosher
        cmd = '%s checkout -f master' % GIT_STRING
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            branch_problem('Could not check out master again')
            continue

        # delete the current branch only if we could switch back to master
        cmd = '%s branch -D pull_%s' % (GIT_STRING, result['number'])
        o, e, r = qiime_system_call(cmd)
        print('deleting the branch')
