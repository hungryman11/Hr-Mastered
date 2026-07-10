from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from core.models import Company, Department, Employee

class BaseModelTests(TestCase):
    def setUp(self):
        # Create a test company
        self.company = Company.objects.create(name="Acme Corp")
        # Create a test employee
        self.employee = Employee.objects.create_user(
            username="johndoe",
            email="john@acme.com",
            password="securepassword123",
            company=self.company
        )

    def test_uuid_generation(self):
        """Verify that UUID is automatically generated and is unique."""
        company2 = Company.objects.create(name="Stark Industries")
        self.assertIsNotNone(self.company.uuid)
        self.assertIsNotNone(company2.uuid)
        self.assertNotEqual(self.company.uuid, company2.uuid)

    def test_soft_delete(self):
        """Verify that delete() soft deletes the record and hides it from default querysets."""
        dept = Department.objects.create(
            name="Engineering",
            company=self.company,
            created_by=self.employee
        )
        dept_id = dept.id

        # Verify it exists in active querysets
        self.assertTrue(Department.objects.filter(id=dept_id).exists())

        # Perform soft delete
        dept.delete()

        # Verify it is hidden from default manager
        self.assertFalse(Department.objects.filter(id=dept_id).exists())

        # Verify it still exists in all_objects manager and has deleted_at set
        deleted_dept = Department.all_objects.get(id=dept_id)
        self.assertIsNotNone(deleted_dept.deleted_at)
        self.assertTrue(deleted_dept.deleted_at <= timezone.now())

    def test_hard_delete(self):
        """Verify that hard_delete() completely removes the record from the database."""
        dept = Department.objects.create(
            name="Marketing",
            company=self.company,
            created_by=self.employee
        )
        dept_id = dept.id

        # Hard delete
        dept.hard_delete()

        # Verify it does not exist anywhere
        self.assertFalse(Department.objects.filter(id=dept_id).exists())
        self.assertFalse(Department.all_objects.filter(id=dept_id).exists())

    def test_company_scoped_relation(self):
        """Verify multi-tenancy constraint by scoping records to a Company."""
        dept = Department.objects.create(name="HR", company=self.company)
        self.assertEqual(dept.company, self.company)
        self.assertIn(dept, self.company.department_records.all())
