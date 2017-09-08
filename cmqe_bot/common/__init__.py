import os
import re
import requests
import inspect

from pylarion.work_item import TestCase

from cmqe_bot.conf import conf
from cmqe_bot.git_stat import env
from constants import GITHUB_URL, POLARION_CASE_AUTOMATION_STATUSES


CASE_ID_PATTERN = r'[{}]+-\d+'.format(conf().polarion.project)


def currnet_func_name():
    return inspect.stack()[1][3]


def extract_polarion_case_ids(string):
    return list(set(re.findall(CASE_ID_PATTERN, string, re.IGNORECASE)).union())


def get_test_files_by_cases():
    """Getting the test files by polarion test case ID.
    Returns:
        LUT (dict) of <case_id>: <filename>.
    """
    case_2_file = {}

    for file_ in env().REPO.get_file_contents(conf().github.tracked_dir):
        full_url = os.path.join(
            '{}/{}/{}/tree/master'.format(GITHUB_URL, conf().github.org, conf().github.repo),
            file_.path)
        for case_id in extract_polarion_case_ids(file_.decoded_content):
            case_2_file[case_id] = full_url

    return case_2_file


def get_automation_statuses_from_github():
    """Getting the automation statuses from GitHub by going over the merged code and the
    pull requests, for each pull request it checks the status of the PR.
    Returns:
        LUT (dict) of the automation statuses (not including NOT_AUTOMATED).
    """
    from cmqe_bot.git_stat.pull_request_status import PullRequestStatusCollection, PR_STATUSES
    statuses = PullRequestStatusCollection(logins=conf().users)

    review_pids, progress_pids = set(), set()
    for status in statuses:
        diff = requests.get(status.diff_url).content
        pids = extract_polarion_case_ids(diff)
        if status.status == PR_STATUSES.RFR.value:
            review_pids.update(pids)
        else:
            progress_pids.update(pids)

    automated = set()
    for file_ in env().REPO.get_file_contents(conf().github.tracked_dir):
        automated.update(extract_polarion_case_ids(file_.decoded_content))

    inreview = review_pids - automated
    inprogress = progress_pids - automated

    return {
            POLARION_CASE_AUTOMATION_STATUSES.INPROGRESS: inprogress,
            POLARION_CASE_AUTOMATION_STATUSES.INREVIEW: inreview,
            POLARION_CASE_AUTOMATION_STATUSES.AUTOMATED: automated
            }


def get_automation_statuses_from_polarion():

    polarion_items = TestCase.query('project.id:{}'.format(conf().polarion.project))

    LUT = {stat: set() for stat in POLARION_CASE_AUTOMATION_STATUSES}

    for item in polarion_items:
        test_case = TestCase(uri=item.uri)
        # TODO: Check whether we have the ID as property of test_case
        item_id = extract_polarion_case_ids(item.uri).pop()
        caseautomation = test_case.caseautomation
        print '{} - {}'.format(item_id, caseautomation)
        if caseautomation not in LUT:
            LUT[caseautomation] = set()
        LUT[caseautomation].add(item_id)

    return LUT
