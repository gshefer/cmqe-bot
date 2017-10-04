# -*- coding: utf-8 -*-
import ssl
import traceback
import argparse
import logging
import os

from pylarion.work_item import TestCase

from cmqe_bot.common import get_automation_statuses_from_github, get_test_files_by_cases,\
    extract_polarion_case_ids
from cmqe_bot.common.constants import POLARION_CASE_AUTOMATION_STATUSES
from cmqe_bot.conf import conf


"""
Updating polarion test cases status according to the pull requests and the current
tests in master.
Fetching the following values:
    * Automation - Searching for the polarion cases (as comment or marker) in each test file.
                   If it's in master - Automated, if it's in PR, define the automation status
                   according to the PR status.
    * Automation Script.
    # TODO: Add fetching of the Automation assignee.
"""


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--ignore-automated', default=False,
                        dest='ignore_automated', action='store_true',
                        help='Ignore test cases of status AUTOMATED '
                             '(i.e. keep them as AUTOMATED even that they '
                             'have not being detected as automated)')
    parser.add_argument('--log-file', default='', dest='log_file', help='Output log file.')
    args = parser.parse_args()
    return args


def set_field(obj, fld_name, value):
    """Set the value to the object field,
    if the value is equal to the current field value, doesn't do anything,
    else return True"""
    cur_value = getattr(obj, fld_name)
    if isinstance(cur_value, (unicode)):
        cur_value = cur_value.encode('utf-8')
    if cur_value != value:
        logger.info('Updating {}: "{}" --> "{}"'.format(fld_name, cur_value, value))
        setattr(obj, fld_name, value)
        return True


def main():

    args = parse_cmd_line()

    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if args.log_file:
        log_dirname = os.path.dirname(args.log_file) or os.getcwd()
        if not os.path.isdir(log_dirname):
            raise IOError('No such directory: "{}"'.format(log_dirname))
        handler = logging.FileHandler(args.log_file)
        logger.addHandler(handler)

    ssl._create_default_https_context = ssl._create_unverified_context
    polarion_items = TestCase.query('project.id:{}'.format(conf().polarion.project))

    logger.info('{} test cases were found'.format(len(polarion_items)))

    logger.info('Getting automation statuses from GitHub...')
    automation_stats = get_automation_statuses_from_github()
    for key, val in automation_stats.items():
        logger.info('    {} = {}'.format(key, len(val)))

    files_by_cases = get_test_files_by_cases()

    for item in polarion_items:

        test_case = TestCase(uri=item.uri)
        case_id = extract_polarion_case_ids(item.uri).pop()

        logger.info('Checking test case: {};'.format(case_id))
        case_found, needs_update = False, False

        for status, cases in automation_stats.items():

            if case_id in cases:
                needs_update = (set_field(test_case, 'caseautomation', status)
                                or needs_update)
                script_url = files_by_cases.get(case_id, None)
                needs_update = set_field(test_case, 'automation_script', script_url) or needs_update
                needs_update = set_field(test_case, 'status', 'approved') or needs_update
                case_found = True
                break

        if not args.ignore_automated and not case_found and test_case.caseautomation not in \
                (POLARION_CASE_AUTOMATION_STATUSES.MANUALONLY,
                 POLARION_CASE_AUTOMATION_STATUSES.NOT_AUTOMATED,
                 POLARION_CASE_AUTOMATION_STATUSES.INPROGRESS):
            needs_update = (set_field(test_case, 'caseautomation',
                                      POLARION_CASE_AUTOMATION_STATUSES.NOT_AUTOMATED)
                            or needs_update)

        if needs_update:
            try:
                test_case.update()
            except ssl.SSLError:
                logger.warning(traceback.format_exc())
                logger.warning('Failed to save (timeout), retrying...')
                ssl._create_default_https_context = ssl._create_unverified_context
                test_case.update()
            logger.info('test case "{}" has been updated.'.format(case_id))

    logger.info('Finished {}'.format(__file__))

if __name__ == '__main__':

    main()
