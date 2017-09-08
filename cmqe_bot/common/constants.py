from enum import Enum

GITHUB_URL = 'https://github.com'


class ExtendedEnum(Enum):
    @classmethod
    def values(cls):
        return [value.value for value in cls]


class POLARION_CASE_AUTOMATION_STATUSES(ExtendedEnum):
    MANUALONLY = 'manualonly'
    NOT_AUTOMATED = 'notautomated'
    INPROGRESS = 'inprogress'
    INREVIEW = 'inreview'
    AUTOMATED = 'automated'
