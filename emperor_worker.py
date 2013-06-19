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
        print("fetching %s" % url, file=stderr)
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

def run_script_usage_examples(script_path, output_dir=None):
    """ """
    original_dir = getcwd()

    script_name = splitext(basename(script_path))[0]
    script_dir = dirname(abspath(script_path))
    addsitedir(script_dir)
    test_data_dir = join(dirname(script_dir), 'tests/scripts_test_data/%s/' % script_name)
    script = __import__(script_name)

    usage_examples = script.script_info['script_usage']

    copytree(test_data_dir, output_dir)
    chdir(output_dir)

    for example in usage_examples:
        cmd = example[2].replace('%prog',script_name+'.py')
        o, e, _ = qiime_system_call(cmd)

        print(cmd)
        break

    chdir(original_dir)


if __name__ == "__main__":
    try:
        emperor_path = argv[1]
    except IndexError:
        emperor_path = '/home/yova1074/emperor/'
    
    print('The URL is %s' % GITHUB_URL, file=stderr)

    PULL = 'git --git-dir=/Users/yoshikivazquezbaeza/git_sw/emperor/.git pull git://github.com/qiime/emperor.git master'
    e, o, r = qiime_system_call(PULL)

    if r != 0:
        print(e)

    # run_script_usage_examples('/Users/yoshikivazquezbaeza/git_sw/emperor/scripts/make_emperor.py',
    #     '/Users/yoshikivazquezbaeza')

    # pull the latest changes to the local repository at its master branch
    # run all the commands as defined in the usage examples make_emperor.py
    # make sure to do all this in a temporary location so the replacement is
    # as smooth as possible
    # copy all the generated files into the public folder that we have assigned

    # remove anything in the public folder that begins with pull_

    # begin the fun by fetching all of the open pull requests
    try:
        results = get_paged_request(GITHUB_URL)
    except IOError:
        print('Could not establish a connection', file=stderr)

    if len(results) == 0:
        print('No active pull requests, getting the exiting ...')
        exit(0)

    for result in results:
        print('Active pull request "pull_%s"' % result['number'])
        print('URL: %s' % result['head']['repo']['git_url'])
        print('Branch name: %s' % result['head']['ref'])

        cmd = 'git --git-dir=/Users/yoshikivazquezbaeza/git_sw/emperor/.git checkout -b pull_%s' % result['number']
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            continue

        cmd = 'git --git-dir=/Users/yoshikivazquezbaeza/git_sw/emperor/.git pull %s %s' % (result['head']['repo']['git_url'], result['head']['ref'])
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            continue

        cmd = 'git --git-dir=/Users/yoshikivazquezbaeza/git_sw/emperor/.git checkout master'
        o, e, r = qiime_system_call(cmd)
        if r != 0:
            continue

        # run_script_usage_examples('/Users/yoshikivazquezbaeza/git_sw/emperor/scripts/make_emperor.py',
        #     '/Users/yoshikivazquezbaeza')


        # checkout a new branch with the name pull_XX
        # pull from the repository where this pull request is originally located
        # build all the examples in this version of make_emperor.py
        # copy them to the public location
