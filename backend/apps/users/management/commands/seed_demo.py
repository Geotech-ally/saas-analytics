"""
Usage:
  python manage.py seed_demo
  python manage.py seed_demo --org "Acme" --admin admin@acme.com --password Secret123!
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.organizations.models import Organization
from apps.users.models import User


class Command(BaseCommand):
    help = "Seed the database with a demo organization and users."

    def add_arguments(self, parser):
        parser.add_argument("--org", default="Demo Corp", help="Organization name")
        parser.add_argument("--admin", default="admin@demo.com", help="Admin email")
        parser.add_argument("--password", default="Demo1234!", help="Admin password")

    @transaction.atomic
    def handle(self, *args, **options):
        org_name = options["org"]
        slug = org_name.lower().replace(" ", "-")

        org, org_created = Organization.objects.get_or_create(
            slug=slug,
            defaults={"name": org_name, "plan": Organization.Plan.PRO, "max_users": 20},
        )
        if org_created:
            self.stdout.write(self.style.SUCCESS(f"Created organization: {org}"))
        else:
            self.stdout.write(f"Organization already exists: {org}")

        admin_email = options["admin"]
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password=options["password"],
                first_name="Demo",
                last_name="Admin",
                organization=org,
                role=User.Role.ADMIN,
            )
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {admin_email}"))
        else:
            self.stdout.write(f"Admin already exists: {admin_email}")

        # Create two regular users
        sample_users = [
            ("alice@demo.com", "Alice", "Smith"),
            ("bob@demo.com", "Bob", "Jones"),
        ]
        for email, first, last in sample_users:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password=options["password"],
                    first_name=first,
                    last_name=last,
                    organization=org,
                    role=User.Role.USER,
                )
                self.stdout.write(self.style.SUCCESS(f"Created user: {email}"))

        self.stdout.write(self.style.SUCCESS("\n✓ Seed complete."))
        self.stdout.write(f"  Login → {admin_email} / {options['password']}")
