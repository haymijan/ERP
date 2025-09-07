# management/management/commands/backup.py (উন্নত সংস্করণ)
import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates a compressed backup of the database and media files.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE(f"Starting full backup process at {timezone.now()}..."))
        
        try:
            # ডাটাবেস ব্যাকআপ
            self.stdout.write("Backing up database...")
            call_command('dbbackup', '--clean', '--compress')
            self.stdout.write(self.style.SUCCESS('Database backup completed successfully.'))

            # মিডিয়া ফাইল ব্যাকআপ
            self.stdout.write("Backing up media files...")
            call_command('mediabackup', '--clean', '--compress')
            self.stdout.write(self.style.SUCCESS('Media files backup completed successfully.'))
            
            self.stdout.write(self.style.SUCCESS('Full backup process finished.'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred during backup: {e}'))
            return