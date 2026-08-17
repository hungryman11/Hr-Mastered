from django.test import SimpleTestCase
from django.urls import get_resolver


class Phase75ContractTests(SimpleTestCase):
    def test_active_api_routes_do_not_expose_loans(self):
        patterns = '\n'.join(str(pattern.pattern) for pattern in get_resolver().url_patterns)
        self.assertNotIn('loan', patterns.lower())
