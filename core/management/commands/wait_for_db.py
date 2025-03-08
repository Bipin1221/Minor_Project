"""django command to wait for the database to be available."""
from django.core.management.base import BaseCommand
import time
from psycopg2 import OperationalError as psycopg2OpError
from django.db.utils import OperationalError

class Command(BaseCommand):
    """django command to wait for database"""
    def handle (self, *ars, **options):
        """entry point for command."""
        self.stdout.write('waiting for database ...')
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up=True
            except (psycopg2OpError,OperationalError):
                self.stdout.write('Database unavailable, waiting 1 second ...')
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS('Database available'))

            