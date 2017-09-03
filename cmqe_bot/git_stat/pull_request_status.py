# -*- coding: utf-8 -*-
from datetime import datetime
import dateparser
import re
import requests
import time

from . import env
from cmqe_bot.conf import conf
from cmqe_bot.common.constants import ExtendedEnum


class PR_STATUSES(ExtendedEnum):
    # Pull request statuses as they appear in the PR title
    WIP = 'WIP'
    BLOCKED = 'BLOCKED'
    WIPTEST = 'WIPTEST'
    RFR = 'RFR'


class PullRequestStatus(object):

    def __init__(self, pull_request):

        self._pull_request = pull_request
        self._html = None
        self._html_last_refresh = None

    @property
    def pull_request(self):
        return self._pull_request

    @property
    def html(self):
        if not self._html or time.time() - self._html_last_refresh > 60:
            self._html = requests.get(self._pull_request.html_url).content
            self._html_last_refresh = time.time()

        return self._html

    @property
    def patch_url(self):
        return self._pull_request.patch_url

    @property
    def diff_url(self):
        return self._pull_request.diff_url

    @property
    def patch(self):
        return requests.get(self._pull_request.patch_url).content.encode('UTF-8')

    @property
    def diff(self):
        return requests.get(self._pull_request.diff_url).content.encode('UTF-8')

    @property
    def number(self):
        return self._pull_request.number

    @property
    def user(self):
        return getattr(self._pull_request.user, 'name',
                       self._pull_request.user.login)

    @property
    def title(self):
        return self._pull_request.title

    @property
    def status(self):
        return re.findall(r'\[(\w+)\]', self.title)[-1]

    @property
    def age(self):
        now = datetime.now()
        return now - self._pull_request.created_at

    @property
    def review_comments(self):
        comments = [c for c in self._pull_request.get_review_comments()]
        comments.sort(key=lambda c: c.updated_at)
        return comments

    @property
    def last_review_comment(self):
        review_comments = self.review_comments
        if review_comments:
            return max(review_comments, key=lambda item: item.updated_at)

    @property
    def comments(self):
        comments = [c for c in self._pull_request.get_issue_comments()]
        comments.sort(key=lambda c: c.updated_at)
        return comments

    @property
    def prt_results(self):

        check_patterns = map(
            lambda s: re.compile(s, re.IGNORECASE | re.UNICODE),
            [
                r'ci/(downstream-\d+z)[\s\b/\S.<>\w\d]+?(?<=(failure|success))',
                # r'ci/(upstream)[\s\b/\S.<>\w\d]+?(?<=(failure|success))',
                r'code/(lint)[\s\b/\S.<>\w\d]+?([\w\s]+(?=fail|succe)[\w\s]+)',
                # TODO: change to use HTML parser and get also quantified code results
            ]
        )
        checks = []
        for check_pat in check_patterns:
            checks.extend(re.findall(check_pat, self.html))

        checks = list(set(set(checks)).union())

        return checks

    @property
    def owner(self):
        return self._pull_request.user

    @property
    def last_code_update(self):
        return dateparser.parse(list(self.pull_request.get_commits()).pop().last_modified)


class PullRequestStatusCollection(object):

    def __init__(self, *args, **kwargs):

        state = kwargs.get('state', 'open')
        logins = kwargs.get('logins', conf().users)

        logins = [login.lower() for login in logins]

        self.pr_statuses = [
            PullRequestStatus(pr) for pr in env().REPO.get_pulls()
            if pr.user.login.lower() in logins
            and pr.state == state
        ]

    def __iter__(self):
        return iter(self.pr_statuses)

    def dump(self):
        out = []
        for prs in self:
            lst_cmnt = prs.last_review_comment
            prt_results = prs.prt_results
            age_total_seconds = int(prs.age.total_seconds())
            days_ago = age_total_seconds / 86400
            hours_ago = (age_total_seconds - days_ago * 86400) / 3600
            out.append({
                'number': prs.number,
                'owner': prs.owner.name or prs.owner.login,
                'title': prs.title,
                'status': prs.status,
                'age': {
                    'days': days_ago,
                    'hours': hours_ago
                },
                'prt': {r[0]: r[1] for r in prt_results},
                'last_code_update': prs.last_code_update.isoformat()
            })
            if lst_cmnt:
                out[-1]['last_review_comment'] = {
                    'user': lst_cmnt.user.name or lst_cmnt.user.login,
                    'body': lst_cmnt.body,
                    'updated_at': lst_cmnt.updated_at.isoformat()
                }
        return out


if __name__ == '__main__':

    # TODO: Move this test to test directory once created

    pr_statuses = PullRequestStatusCollection()
    pr_statuses.dump()
