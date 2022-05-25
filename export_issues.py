# -*- coding: utf-8 -*-

import csv
import platform
import sys
import time

import requests
from github import Github

if platform.python_version_tuple()[0] == '2':
    print('======Please use python 3.x======')
    input('Press Enter to quit...')
    sys.exit(0)


class LOGIC:
    AND = 0
    OR = 1


def countdown(sec):
    for i in range(sec):
        time.sleep(1)
        print('\r%d seconds left...\t\t' % (sec - i), end='')
    print('ok')


def get_current_time():
    # todo: You can change the url if you use GitHub Enterprise or other servers
    github_time = requests.get('https://api.github.com').headers['Date']  # Use https://*.github.com to get current server time.
    return time.strptime(github_time, '%a, %d %b %Y %H:%M:%S GMT')


def check_remaining():
    remain_cnt = g.get_rate_limit().core.remaining
    print('remain: %d' % remain_cnt)
    if remain_cnt < 50:  # todo: use param?
        reset_time = g.get_rate_limit().core.reset
        cur_time = get_current_time()
        print('wait until: %s' % reset_time.strftime('%Y-%m-%d %H:%M:%S UTC'))
        print('current time: %s' % time.strftime('%Y-%m-%d %H:%M:%S UTC', cur_time))
        wait_time = int(reset_time.timestamp() - time.mktime(cur_time))  # accurate to second is enough
        print('wait %d seconds until reset...' % wait_time)
        countdown(wait_time)


def check_filter(filter_list: list = None, all_list: list = None, logic: int = LOGIC.AND):
    if not filter_list:
        return True  # speed up: always True if filter_list is None
    if logic == LOGIC.AND:
        return set(filter_list) <= set(all_list)
    if logic == LOGIC.OR:
        return [i for i in filter_list if i in all_list] > []


def get_all_issues(state='all', milestone: str = None,
                   required_labels: list[str] = None,
                   labels: list[str] = None, labels_logic=LOGIC.AND,
                   assignees: list[str] = None, assignees_logic=LOGIC.AND):
    issue_list = []
    issues = repo.get_issues(state=state)
    with open('issues.csv', 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # todo: use friendly col name?
        writer.writerow(['id', 'number', 'title', 'labels', 'milestone', 'state', 'assignees', 'closed_at',
                         'created_at', 'last_modified', 'updated_at'])
        check_remaining()
        total = issues.totalCount  # remain -1
        cnt = 0
        print('Writing to issues.csv.....')
        for issue in issues:  # remain -1
            cnt += 1
            print('getting issue %d\t %d/%d' % (issue.number, cnt, total))
            # if issue.pull_request: # remain -1
            #     print('skipping PR %d\t %d/%d' % (issue.number, cnt, total))
            #     print('check pr yes')
            #     check_remaining()
            #     continue
            # print('check pr no')

            # label
            tmp_label = []
            tmp_an = []
            for l in issue.labels:
                tmp_label.append(l.name)
            if not check_filter(required_labels, tmp_label, LOGIC.AND):
                continue
            if not check_filter(labels, tmp_label, labels_logic):
                continue

            # assignees
            for an in issue.assignees:
                if an:
                    # tmp_an.append('%s<%s>' % (an.login, (an.name or an.login)))
                    tmp_an.append(an.login)
                else:
                    tmp_an.append('')
            if not check_filter(assignees, tmp_an, assignees_logic):
                continue

            # c_b = ''  # bad var name, but I'm too lazy...
            # if issue.closed_by: # remain -1
            #     # c_b = '%s<%s>' % (issue.closed_by.login, (issue.closed_by.name or issue.closed_by.login))
            #     c_b = issue.closed_by.login

            # milestone
            tmp_milestone = ''
            if issue.milestone:
                tmp_milestone = issue.milestone.title
            if milestone and not milestone == tmp_milestone:
                continue
            # if cnt % 20 == 0:  # check remaining every 20 issues.
            #     check_remaining()

            line = [issue.id,
                    issue.number,
                    issue.title,
                    ','.join(tmp_label),
                    tmp_milestone,
                    issue.state,
                    ','.join(tmp_an),
                    issue.closed_at,
                    issue.created_at,
                    issue.last_modified,
                    issue.updated_at]
            writer.writerow(line)
    return issue_list


if __name__ == '__main__':
    try:
        # todo: use args?
        g = Github('your access_token here')
        repos = g.get_user().get_repos()
        for repo in repos:
            if repo.full_name == 'org_name/repo_name':
                list_numbers = []
                list_select = []

                print('Retrieving issues......')
                get_all_issues()

        print('====Completed!====')
        input('Press Enter to quit...')
    except Exception as e:
        print("ERROR: ", e)
        input('Press Enter to quit...')
