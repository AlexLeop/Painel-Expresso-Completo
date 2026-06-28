import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='Stop';")
    print("Stop columns:", [row[0] for row in cursor.fetchall()])

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='Order';")
    print("Order columns:", [row[0] for row in cursor.fetchall()])
