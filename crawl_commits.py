#!/usr/bin/env python
# -*-coding: utf8 -*-

import json
import sys
import time
from datetime import datetime
import argparse
import getpass
from os import path, makedirs, listdir
from commitgen.github import GitHub, ApiError

def dump_json(commit, json_path):
    with open(path.join(json_path, commit.sha + ".json"), "w") as json_file:
        json.dump(commit, json_file)


def dump_diff(sha, diff_string, diff_path):
    with open(path.join(diff_path, sha + ".diff"), "w") as diff_file:
        try:
            diff_file.write(diff_string.encode("utf-8"))
        except Exception as e:
            print e

def remaining(gh):
    result = int(gh.x_ratelimit_remaining)
    if result == -1:
        return 1
    return result


def reset_time(gh):
    return gh.x_ratelimit_reset


def get_commit_info(gh, account, project, json_path):
    commits_url = gh.repos(account)(project).commits
    more = True
    per_page = 500
    page = 2
    existing_json_files = [filename.replace('.json', '')
                           for filename in listdir(json_path)]
    tries = 0
    while more:
        if remaining(gh) > 0:
            try:
                response, more = commits_url.get(page=page, per_page=per_page)
                if response:
                    for commit in response:
                        if commit.sha not in existing_json_files:
                            dump_json(commit, json_path)
                page += 1
                print "Page " + str(page)
                print "Remaining Quota:  " + str(remaining(gh))
            except ApiError as e:
                print e
        else:
            reset_time_value = reset_time(gh)
            print "Waiting until " + str(datetime.fromtimestamp(reset_time_value))
            waiting_time = reset_time_value - time.time()
            if waiting_time > 0:
                time.sleep(waiting_time)
            else:
                if tries > 10:
                    print "Waited too long and quota did not update, please try again later."
                    break
                print "Waiting one extra minute to allow for quota update..."
                time.sleep(60)
                tries += 1


def get_diff_files(gh, account, project, json_path, diff_path):
    commits_url = gh.repos(account)(project).commits
    existing_diff_files = [filename.replace('.diff', '')
                           for filename in listdir(diff_path)]

    json_files = listdir(json_path)

    for i, filename in enumerate(json_files):
        sha = filename.replace(".json", "")
        if sha not in existing_diff_files:
            if remaining(gh):
                try:
                    response, more = commits_url(sha).get()
                    dump_diff(sha, response, diff_path)
                except ApiError as e:
                    print e
                    print "Maybe diff file was too big?"
            else:
                print "Waiting until " + str(datetime.fromtimestamp(reset_time(gh)))
                waiting_time = reset_time(gh) - round(time.time(), 0) + 10
                time.sleep(waiting_time)

        print '[progress] >> %2.2f%%\r' % (float(i)/len(json_files)*100.),
        sys.stdout.flush()


if __name__ == "__main__":

    desc = "Help for crawl_commits"

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("download_path",
                        help="Path to download commits")

    parser.add_argument("account",
                        type=str,
                        help="Github account name")

    parser.add_argument('project',
                        type=str,
                        help="Project Name")

    parser.add_argument('--username', "-u",
                        type=str,
                        default=None,
                        help="Github account username to log in GitHub")

    parser.add_argument("--metadata", "-m",
                        action='store_true',
                        help="To download metadata")

    parser.add_argument("--diff", "-d",
                        action='store_true',
                        help="To download diff files")

    args = parser.parse_args()


    if args.username:
        password = getpass.getpass()
        gh = GitHub(username=args.username, password=password)
    else:
        gh = GitHub()

    download_path = path.join(args.download_path, args.project + "_commits")

    print "Downloading data for project " + args.account  + "/" + args.project
    print  "download_path = " + download_path

    # create folders
    diff_path = path.join(download_path, "diff")
    if not path.isdir(diff_path):
        makedirs(diff_path)

    json_path = path.join(download_path, "json")
    if not path.isdir(json_path):
        makedirs(json_path)

    if args.metadata:
        get_commit_info(gh, args.account, args.project, json_path)

    if args.diff:
        get_diff_files(gh, args.account, args.project, json_path, diff_path)
