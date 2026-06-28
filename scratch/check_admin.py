import os
import sys
import django
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import PlatformAdmin, StaffMember

admins = PlatformAdmin.objects.all()
print("--- Platform Admins ---")
for admin in admins:
    print(f"ID: {admin.id}, Name: {admin.name}, Email: {admin.email}, SupabaseUID: {admin.supabase_uid}")

staffs = StaffMember.objects.all()
print("\n--- Staff Members ---")
for staff in staffs:
    print(f"ID: {staff.id}, Name: {staff.name}, Email: {staff.email}, SupabaseUID: {staff.supabase_uid}, Role: {staff.role}, Active: {staff.active}")
