# management/views.py (চূড়ান্ত এবং নিরাপদ সমাধান)

import os
import traceback
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.conf import settings
from datetime import datetime
from django.core.management import call_command
from django.shortcuts import redirect

@user_passes_test(lambda u: u.is_superuser)
def backup_restore_view(request):
    
    # ব্যাকআপ তৈরির জন্য POST অনুরোধ (ডাটাবেস + মিডিয়া ফাইল)
    if request.method == 'POST' and 'create_backup' in request.POST:
        try:
            call_command('dbbackup', '--clean', '--compress', verbosity=0)
            call_command('mediabackup', '--clean', '--compress', verbosity=0)
            messages.success(request, "New Database and Media files backup created successfully!")
        except Exception as e:
            messages.error(request, f"Backup creation failed: {e}")
            traceback.print_exc()
        return HttpResponseRedirect(request.path_info)

    # শুধুমাত্র মিডিয়া ফাইল রিস্টোর করার জন্য POST অনুরোধ
    if request.method == 'POST' and 'restore_media' in request.POST:
        filename_to_restore = request.POST.get('filename')
        backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location')
        
        if not filename_to_restore:
            messages.error(request, "No media backup file selected for restore.")
        else:
            full_path = os.path.join(backup_dir, filename_to_restore)
            try:
                call_command('mediarestore', input_path=full_path, uncompress=True, interactive=False)
                messages.success(request, f"Successfully restored media files from {filename_to_restore}.")
            except Exception as e:
                messages.error(request, f"Media restore failed: {e}")
                traceback.print_exc()
        return HttpResponseRedirect(request.path_info)

    # ব্যাকআপ ফাইলের তালিকা দেখানো
    backup_files = []
    backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location')
    try:
        if backup_dir and os.path.isdir(backup_dir):
            filenames = sorted(os.listdir(backup_dir), reverse=True)
            for f in filenames:
                if f.endswith(('.gz', '.dump', '.tar')):
                    file_path = os.path.join(backup_dir, f)
                    is_db = '.psql' in f or '.sqlite' in f
                    backup_files.append({
                        'name': f,
                        'size': os.path.getsize(file_path),
                        'date': datetime.fromtimestamp(os.path.getmtime(file_path)),
                        'is_db': is_db
                    })
        else:
             messages.warning(request, f"Backup directory not found at: {backup_dir}")
    except Exception as e:
        messages.error(request, f"Could not list backup files: {e}")

    context = {
        'title': 'Backup & Restore',
        'backup_files': backup_files,
        'storage_path': backup_dir or 'Not configured'
    }
    return render(request, 'management/backup_restore.html', context)

@user_passes_test(lambda u: u.is_superuser)
def delete_backup_view(request, filename):
    if request.method == 'POST':
        backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location')
        file_path = os.path.join(backup_dir, filename)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                messages.success(request, f"Backup file '{filename}' deleted successfully.")
            else:
                messages.error(request, f"File '{filename}' not found.")
        except Exception as e:
            messages.error(request, f"Error deleting file: {e}")
            
    return redirect('management:backup_restore')