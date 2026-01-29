import os
from django.db.models import Max
from django.utils.timezone import now

from .models import Task, SyncStatus
from .views import get_sheet_service
import os
from dotenv import load_dotenv
from pathlib import Path
from django.conf import settings
env_path = Path(settings.BASE_DIR) / '.env'
load_dotenv(dotenv_path=env_path)

def auto_sync_google_sheet():
    log_path = "/tmp/django_cron.log"
    
    with open(log_path, "a") as f:
        # 1. Fetch data
        sync_status, _ = SyncStatus.objects.get_or_create(id=1)
        latest_task_update = Task.objects.aggregate(Max("updated_at"))["updated_at__max"]

        if not latest_task_update:
            f.write(f"[{now()}] No tasks found. Skipping.\n")
            return

        # 2. Logic Check with Logging
        if sync_status.last_synced_at:
            # We use a 1-second buffer to prevent loop syncs or micro-mismatches
            if latest_task_update <= sync_status.last_synced_at:
                f.write(f"[{now()}] No new changes (Latest: {latest_task_update} | Last Sync: {sync_status.last_synced_at})\n")
                return

        f.write(f"[{now()}] Changes detected. Starting Google Sheets Sync...\n")

        try:
            service = get_sheet_service()
            sheet = service.spreadsheets()
            
            # Get ID from env (already loaded via load_dotenv)
            spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
            
            values = []
            for task in Task.objects.all().order_by("position"):
                values.append([
                    task.id, task.task, task.status,
                    str(task.created_at), str(task.started_at or ""),
                    str(task.completed_at or ""), task.position,
                ])

            # Sync
            sheet.values().clear(spreadsheetId=spreadsheet_id, range="Sheet1!A2:G").execute()
            sheet.values().update(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A2:G",
                valueInputOption="RAW",
                body={"values": values}
            ).execute()

            # Update SyncStatus only AFTER successful API call
            sync_status.last_synced_at = now()
            sync_status.save()
            f.write(f"[{now()}] Sync Successful.\n")

        except Exception as e:
            f.write(f"[{now()}] SYNC ERROR: {str(e)}\n")