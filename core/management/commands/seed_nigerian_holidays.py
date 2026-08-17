from datetime import date
from django.core.management.base import BaseCommand
from core.models import Company, CompanyHoliday


class Command(BaseCommand):
    help = 'Seeds standard Nigerian public holidays for 2024-2027.'

    HOLIDAYS = [
        # 2024
        ("New Year's Day", date(2024, 1, 1)),
        ("Good Friday", date(2024, 3, 29)),
        ("Easter Monday", date(2024, 4, 1)),
        ("Eid el-Fitr", date(2024, 4, 10)),
        ("Workers' Day", date(2024, 5, 1)),
        ("Democracy Day", date(2024, 6, 12)),
        ("Eid el-Kabir", date(2024, 6, 16)),
        ("Independence Day", date(2024, 10, 1)),
        ("Christmas Day", date(2024, 12, 25)),
        ("Boxing Day", date(2024, 12, 26)),

        # 2025
        ("New Year's Day", date(2025, 1, 1)),
        ("Good Friday", date(2025, 4, 18)),
        ("Easter Monday", date(2025, 4, 21)),
        ("Eid el-Fitr", date(2025, 3, 31)),
        ("Workers' Day", date(2025, 5, 1)),
        ("Democracy Day", date(2025, 6, 12)),
        ("Eid el-Kabir", date(2025, 6, 7)),
        ("Independence Day", date(2025, 10, 1)),
        ("Christmas Day", date(2025, 12, 25)),
        ("Boxing Day", date(2025, 12, 26)),

        # 2026
        ("New Year's Day", date(2026, 1, 1)),
        ("Good Friday", date(2026, 4, 3)),
        ("Easter Monday", date(2026, 4, 6)),
        ("Eid el-Fitr", date(2026, 3, 20)),
        ("Workers' Day", date(2026, 5, 1)),
        ("Democracy Day", date(2026, 6, 12)),
        ("Eid el-Kabir", date(2026, 5, 27)),
        ("Independence Day", date(2026, 10, 1)),
        ("Christmas Day", date(2026, 12, 25)),
        ("Boxing Day", date(2026, 12, 26)),

        # 2027
        ("New Year's Day", date(2027, 1, 1)),
        ("Good Friday", date(2027, 3, 26)),
        ("Easter Monday", date(2027, 3, 29)),
        ("Eid el-Fitr", date(2027, 3, 9)),
        ("Workers' Day", date(2027, 5, 1)),
        ("Democracy Day", date(2027, 6, 12)),
        ("Eid el-Kabir", date(2027, 5, 16)),
        ("Independence Day", date(2027, 10, 1)),
        ("Christmas Day", date(2027, 12, 25)),
        ("Boxing Day", date(2027, 12, 26)),
    ]

    def handle(self, *args, **options):
        companies = Company.objects.all()
        if not companies.exists():
            self.stdout.write(self.style.WARNING("No companies found. Seed demo or create a company first."))
            return

        total_created = 0
        for company in companies:
            for name, h_date in self.HOLIDAYS:
                _, created = CompanyHoliday.objects.get_or_create(
                    company=company,
                    date=h_date,
                    defaults={'name': name, 'is_national': True}
                )
                if created:
                    total_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_created} holiday entries across {companies.count()} company/companies."))
