# -*- coding: utf-8 -*-

import csv
import os.path
import platform
import smtplib
import sys
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from github import Github

if platform.python_version_tuple()[0] == '2':
    print('======Please use python 3.x======')
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
    # todo: Use https://*.github.com to get current server time.
    # You can change the url if you use other server (e.g. GitHub Enterprise)
    github_time = requests.get('https://api.github.com').headers['Date']
    return time.strptime(github_time, '%a, %d %b %Y %H:%M:%S GMT')


def check_remaining(cnt=500):
    remain_cnt = g.get_rate_limit().core.remaining
    print('remain: %d' % remain_cnt)
    if remain_cnt < cnt:
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
    with open(os.path.join(os.path.dirname(__file__), "issues.csv"), 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # todo: use friendly col name?
        writer.writerow(['id', 'number', 'title', 'labels', 'milestone', 'state', 'assignees', 'closed_at',
                         'created_at', 'last_modified', 'updated_at'])
        check_remaining()
        cnt = 0
        print('Writing to issues.csv.....')
        for issue in issues:  # remain -1
            if cnt % 400 == 0:  # check remaining every 400 issues.
                check_remaining()
            cnt += 1

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

            # milestone
            tmp_milestone = ''
            if issue.milestone:
                tmp_milestone = issue.milestone.title
            if milestone and not milestone == tmp_milestone:
                continue

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
            issue_list.append(line)
            writer.writerow(line)
    return issue_list


def write_html(list_issue, url):
    """
    Create a simple table here as an example. 
    """
    
    html_1 = """
    <!DOCTYPE html>
    <html lang="en">
    <style>
    table, th, td {
      border: 1px solid;
      border-collapse: collapse;
    }
    th, td {
      padding: 5px;
    }
    </style>
    <body>
    <table>
        <tr>
            <th>id</th>
            <th>title</th>
        </tr>
    """

    html_2 = """
    </table>
    </body>
    </html>"""

    html_issue = ''
    for i in list_issue:
        str_id = i[1]
        str_title = i[2]
        html_issue += """
            <tr>
            <td><a href="{2}/{0}">{0}</a></td>
            <td>{1}</td>
            </tr>""".format(str_id, str_title, url)
    html_issues = html_1 + html_issue + html_2
    return html_issues


def send_mail(mail_body, mail_from, mail_to, username, password, mail_host, mail_port=587):
    mail_subject = "Issue Lists"
    mail_attachment = os.path.join(os.path.dirname(__file__), "issues.csv")
    mail_attachment_name = "issues.csv"

    mime_msg = MIMEMultipart()
    mime_msg['From'] = mail_from
    mime_msg['To'] = mail_to
    mime_msg['Subject'] = mail_subject
    mime_msg.attach(MIMEText(mail_body, 'html'))

    with open(mail_attachment, "rb") as attachment:
        mimefile = MIMEBase('application', 'octet-stream')
        mimefile.set_payload(attachment.read())
        encoders.encode_base64(mimefile)
        mimefile.add_header('Content-Disposition', "attachment; filename= %s" % mail_attachment_name)
        mime_msg.attach(mimefile)
        connection = smtplib.SMTP(host=mail_host, port=mail_port)
        connection.starttls()
        connection.login(username, password)
        connection.send_message(mime_msg)
        connection.quit()


if __name__ == '__main__':
    try:
        # todo: use args?
        g = Github('your access_token here')
        repos = g.get_user().get_repos()
        for repo in repos:
            if repo.full_name == 'org_name/repo_name':
                issues_url = repo.html_url + '/issues'
                print('Retrieving issues......')
                # Example: has labels "product1" and "UI", and has the label "high" or "medium"
                i_list = get_all_issues(required_labels=['product1', 'UI'],
                                        labels=['high', 'medium'], labels_logic=LOGIC.OR)
                html_content = write_html(i_list, issues_url)
                send_mail(html_content, 'from@domain.com', 'to@domain.com', 'user', 'password', 'mail.domain.com')

        print('====Completed!====')
    except Exception as e:
        print("ERROR: ", e)
