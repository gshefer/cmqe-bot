from cmqe_bot.git_stat.pull_request_status import PullRequestStatusCollection


def test_pr_statuses():
    pr_statuses = PullRequestStatusCollection()
    pr_statuses.dump()