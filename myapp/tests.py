from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from myapp.models import Task
from unittest.mock import patch, MagicMock
class TaskModelTest(TestCase):

    def test_task_creation_defaults(self):
        task = Task.objects.create(task="Test Task")

        self.assertEqual(task.task, "Test Task")
        self.assertEqual(task.status, "Not Started")
        self.assertIsNotNone(task.created_at)

    def test_duration_not_completed(self):
        task = Task.objects.create(task="No Duration")
        self.assertEqual(task.duration(), "-")

    def test_duration_completed(self):
        start = timezone.now()
        end = start + timedelta(minutes=30)

        task = Task.objects.create(
            task="Duration Task",
            status="Completed",
            started_at=start,
            completed_at=end
        )

        self.assertEqual(task.duration(), "0:30:00")

class DashboardAuthTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_after_login(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard.html")

class TaskActionsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            password="pass"
        )
        self.client.login(username="user", password="pass")

    def test_add_task(self):
        response = self.client.post(reverse("dashboard"), {
            "task": "New Task"
        })

        self.assertEqual(Task.objects.count(), 1)
        self.assertRedirects(response, reverse("dashboard"))

    def test_start_task(self):
        task = Task.objects.create(task="Start Me")

        self.client.get(reverse("start_task", args=[task.id]))
        task.refresh_from_db()

        self.assertEqual(task.status, "In Progress")
        self.assertIsNotNone(task.started_at)

    def test_complete_task(self):
        task = Task.objects.create(
            task="Complete Me",
            status="In Progress"
        )

        self.client.get(reverse("complete_task", args=[task.id]))
        task.refresh_from_db()

        self.assertEqual(task.status, "Completed")
        self.assertIsNotNone(task.completed_at)

    def test_delete_task(self):
        task = Task.objects.create(task="Delete Me")

        response = self.client.get(reverse("delete_task", args=[task.id]))

        self.assertEqual(Task.objects.count(), 0)
        self.assertRedirects(response, reverse("dashboard"))

class TaskFilterTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="filteruser",
            password="pass"
        )
        self.client.login(username="filteruser", password="pass")

        Task.objects.create(task="Pending", status="Not Started")
        Task.objects.create(task="Doing", status="In Progress")
        Task.objects.create(task="Done", status="Completed")

    def test_filter_completed(self):
        response = self.client.get(reverse("dashboard") + "?status=Completed")
        tasks = response.context["tasks"]

        self.assertEqual(tasks.count(), 1)
        self.assertEqual(tasks.first().status, "Completed")

class CSVTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="csvuser",
            password="pass"
        )
        self.client.login(username="csvuser", password="pass")

    def test_export_csv(self):
        Task.objects.create(task="Export Me")

        response = self.client.get(reverse("export_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("task,status", response.content.decode())

    def test_import_csv(self):
        csv_data = (
            "task,status,created_at,started_at,completed_at\n"
            "Imported Task,Not Started,2026-01-01T10:00:00Z,,\n"
        )

        file = SimpleUploadedFile(
            "tasks.csv",
            csv_data.encode(),
            content_type="text/csv"
        )

        _response = self.client.post(
            reverse("import_csv"),
            {"file": file}
        )

        self.assertEqual(Task.objects.count(), 1)

    def test_import_no_duplicates(self):
        csv_data = (
            "task,status,created_at,started_at,completed_at\n"
            "Unique Task,Not Started,2026-01-01 10:00:00,,\n"
        )

        file1 = SimpleUploadedFile("tasks.csv", csv_data.encode(), "text/csv")
        file2 = SimpleUploadedFile("tasks.csv", csv_data.encode(), "text/csv")

        self.client.post(reverse("import_csv"), {"file": file1})
        self.client.post(reverse("import_csv"), {"file": file2})

        self.assertEqual(Task.objects.count(), 1)

class TaskOrderTest(TestCase):
    def setUp(self):
        self.t1 = Task.objects.create(task="Task 1", position=1)
        self.t2 = Task.objects.create(task="Task 2", position=2)

    def test_update_task_order(self):
        # Swap positions
        data = [
            {"id": self.t1.id, "position": 2},
            {"id": self.t2.id, "position": 1}
        ]
        response = self.client.post(
            reverse("update_task_order"),
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.t1.refresh_from_db()
        self.t2.refresh_from_db()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.t1.position, 2)
        self.assertEqual(self.t2.position, 1)

class InlineEditTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="editor", password="pass")
        self.client.login(username="editor", password="pass")
        self.task = Task.objects.create(task="Old Name")

    def test_ajax_update_task(self):
        response = self.client.post(
            reverse("update_task", args=[self.task.id]),
            {"task": "Updated Name"}
        )
        
        self.task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.task.task, "Updated Name")

    def test_ajax_update_empty_fails(self):
        response = self.client.post(
            reverse("update_task", args=[self.task.id]),
            {"task": ""}
        )
        self.assertEqual(response.status_code, 400)



class GoogleSheetsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="syncuser", password="pass")
        self.client.login(username="syncuser", password="pass")
        Task.objects.create(task="Sync Task", position=1)

    @patch('myapp.views.get_sheet_service') # Adjust 'myapp' to your app name
    @patch('os.getenv')
    def test_sync_to_google_sheets(self, mock_env, mock_service):
        # Setup mocks
        mock_env.return_value = "dummy_id"
        mock_sheet = MagicMock()
        mock_service.return_value.spreadsheets.return_value = mock_sheet
        
        response = self.client.get(reverse("sync_google_sheet"))
        
        # Verify redirect
        self.assertRedirects(response, reverse("dashboard"))
        # Verify clear and update were called
        self.assertTrue(mock_sheet.values().clear.called)
        self.assertTrue(mock_sheet.values().update.called)
