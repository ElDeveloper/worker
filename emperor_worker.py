#!/usr/bin/env python
from __future__ import print_function

__author__ = "Yoshiki Vazquez-Baeza"
__license__ = "GPL"
__version__ = "1.0.0-dev"
__maintainer__ = "Yoshiki Vazquez-Baeza"
__email__ = "yoshiki89@gmail.com"
__status__ = "Use at your own risk"

from urllib import urlopen
from json import load as load_json
from subprocess import check_output
from re import compile as re_compile
from datetime import datetime, timedelta

from site import addsitedir
from os import chdir, getcwd
from sys import argv, stderr
from shutil import copytree, rmtree
from os.path import split as path_split
from subprocess import Popen, PIPE, STDOUT
from os.path import abspath, dirname, join, basename, splitext, exists

# https://api.github.com/repos/qiime/emperor/pulls
#curl -i https://api.github.com/repos/qiime/emperor | less -S

GITHUB_URL = "https://api.github.com/repos/qiime/emperor/pulls"
ELEMENT_PAT = re_compile(r'<(.+?)>')
REL_PAT = re_compile(r'rel=[\'"](\w+)[\'"]')

GENERIC_INDEX = """<!DOCTYPE html>
<html>
<body>
<h1>Examples built from <a href="%s">%s</a></h1>
%s
</body>
</html>"""

GENERIC_LINK = """<br><a href="%s">%s</a>
"""

# Taken from matplotlibs tools/github_stats.py
def parse_link_header(headers):
    link_s = headers.get('link', '')
    urls = ELEMENT_PAT.findall(link_s)
    rels = REL_PAT.findall(link_s)
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

# obviously this was taken from QIIME qiime/util.py
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
    """Heavily based on QIIME's/QCLI's script usage testing """
    original_dir = getcwd()
    chdir(dirname(output_dir))
    print ('Currently at %s' % getcwd())
    string_to_write = GENERIC_INDEX
    links = []

    try:
        rmtree(output_dir)
    except OSError, e:
        pass

    # retrieve multi-purpose variables
    script_name = splitext(basename(script_path))[0]
    script_dir = dirname(abspath(script_path))

    # add the folder where the scripts are located
    addsitedir(script_dir)
    test_data_dir = join(dirname(script_dir), 'tests/scripts_test_data/%s/' % script_name)

    # import the script of interest
    script = __import__(script_name)

    # retrieve the dictionary of usage examples, where the actual command is the
    # third element in the tuple, remember that %prog should be replaced by the
    # name of the script that needs to be tested right now
    usage_examples = script.script_info['script_usage']

    o, e, _ = qiime_system_call('git --git-dir=/home/yova1074/emperor/.git branch')
    print(o, e)
    #raw_input('Before compying the data from %s to %s ' % (test_data_dir, output_dir))
    copytree(test_data_dir, output_dir)
    #raw_input('Once the data has been copied')
    chdir(output_dir)
    print(getcwd())

    for example in usage_examples:
        cmd = example[2].replace('%prog',script_name+'.py')
#        o, e, _ = qiime_system_call(cmd)

        # we should get the output name for the folder
        name = cmd.split('-o')[1].split(' ')[1]
        links.append(GENERIC_LINK % (join(name, 'index.html'), name))

        rmtree(name)
        print('Deleting %s' % name)
        #raw_input('This folder has been delated %s' % name)
        o, e, _ = qiime_system_call(cmd)
        print("Running: " + cmd)
        if o: print(o)
        if e: print(e)

    fd = open('index.html', 'w')
    if basename(output_dir) == 'master':
        fd.write(GENERIC_INDEX % ("https://github.com/qiime/emperor/tree/master", basename(output_dir), ''.join(links)))
    else:
        fd.write(GENERIC_INDEX % ("https://github.com/qiime/emperor/pull/"+basename(output_dir).split('_')[1], basename(output_dir), ''.join(links)))
    fd.close()

    chdir(original_dir)


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

    #print('The URL is %s' % GITHUB_URL, file=stderr)

    PULL = '%s pull git://github.com/qiime/emperor.git master' % GIT_STRING
    e, o, r = qiime_system_call(PULL)

    if r != 0:
        print('Could not pull from master, not continuing.')
        print(o)
        print(e)
        exit(0)

    script_path = join(emperor_path, 'scripts/make_emperor.py')
    run_script_usage_examples(script_path, master_path)

    # begin the fun by fetching all of the open pull requests
    try:
        results = get_paged_request(GITHUB_URL)
    except IOError:
        print('Could not establish a connection', file=stderr)

    if len(results) == 0:
        print('No active pull requests, getting the exiting ...')
        exit(0)

    #print('I do not know what is going on with this')
    #exit(1111);

    for result in results:
        print('Active pull request "pull_%s"' % result['number'])
        print('URL: %s' % result['head']['repo']['git_url'])
        print('Branch name: %s' % result['head']['ref'])

        deploying_folder = join(dirname(master_path), 'pull_'+str(result['number']))

        # create a new branch whre this open pull request will live
        cmd = '%s checkout -b pull_%s' % (GIT_STRING, result['number'])
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            continue

        # pull stuff from the branch in question
        cmd = '%s pull %s %s' % (GIT_STRING, result['head']['repo']['git_url'], result['head']['ref'])
        o, e, r = qiime_system_call(cmd)

        # once we pull whether or not it's right i. e. no conflicts, remove the
        # previous folder to ensure there are no confusions with the data
        try:
            rmtree(deploying_folder)
        except OSError:
            pass

        # if something went wrong with the system call then clean all unusable
        # files, reset the repository to the latest head and force a checkout
        # of the master branch in the current repository so any of the other
        # pull requests that are open are not affected by this problem
        if r != 0:
            print('Could not pull the latest changes trying to clean the folder ...')
            print('Could not pull the latest changes trying to clean the folder ...')
            cmd = '%s clean -xdf' % GIT_STRING
            o, e, r = qiime_system_call(cmd)
            #print(o, e)
            cmd = '%s reset --hard HEAD' % GIT_STRING
            o, e, r = qiime_system_call(cmd)
            #print(o, e)
            cmd = '%s checkout -f master' % GIT_STRING
            o, e, r = qiime_system_call(cmd)
            #print(o, e)

            # delete the current branch
            cmd = '%s branch -D pull_%s' % (GIT_STRING, result['number'])
            o, e, r = qiime_system_call(cmd)
            #print(o, e)

            continue

        o, e, _ = qiime_system_call('%s branch' % GIT_STRING)
        print(o)
        o, e, _ = qiime_system_call('%s rev-parse HEAD' % GIT_STRING)
        print(o)

        # if nothing went wrong, run the script usage examples that will finally
        # let you see the rendered examples for this pull request
        run_script_usage_examples(script_path, deploying_folder)

        # go back to master so everything is safely kosher
        cmd = '%s checkout -f master' % GIT_STRING
        o, e, r = qiime_system_call(cmd)
        print('Checking out the master branch')
        #if o: print(o)
        #if e: print(e)

        if r != 0:
            continue

        # delete the current branch only if we could switch back to master
        cmd = '%s branch -D pull_%s' % (GIT_STRING, result['number'])
        o, e, r = qiime_system_call(cmd)
        print('deleting the branch')
        #if o: print(o)
        #if e: print(e)


