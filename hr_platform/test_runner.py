from django.test.runner import DiscoverRunner


class ProjectTestRunner(DiscoverRunner):
    """
    Django's DiscoverRunner only picks up files matching `test*.py` by
    default (e.g. tests.py, test_foo.py). This project also has files named
    `*_tests.py` (security_tests.py, delivery_tests.py, payroll_tests.py,
    loan_tests.py, loan_security_tests.py, integration_tests.py) which do
    NOT match that pattern and were therefore silently excluded from
    `manage.py test` / CI's coverage-gated test run, despite containing real
    tests.

    This subclass just widens the default --pattern so both naming styles
    are discovered, while still letting `-p` override it explicitly if
    someone needs to run a narrower set.
    """

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        for action in parser._actions:
            if '--pattern' in action.option_strings:
                action.default = '*test*.py'
