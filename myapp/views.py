from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Task
import csv
import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.db import IntegrityError
from django.utils.dateparse import parse_datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def get_sheet_service():
    """
    Creates and returns Google Sheets service using service account
    """
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_KEY")

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    return build("sheets", "v4", credentials=creds)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password"
            })

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    if request.method == "POST":
        task = request.POST.get("task")
        if task:
            Task.objects.create(task=task)
        return redirect("dashboard")

    if request.method == "POST":
        task_name = request.POST.get("task")
        if task_name:
            max_pos = Task.objects.aggregate(Max("position"))["position__max"] or 0
            Task.objects.create(
                task=task_name,
                position=max_pos + 1
            )
        return redirect("dashboard")

    tasks = Task.objects.all().order_by("position")
    filters= request.GET.get("status")

    if filters:
        tasks = tasks.filter(status=filters)
    stats = {
        "total": tasks.count(),
        "completed": tasks.filter(status="Completed").count(),
        "pending": tasks.filter(status="Not Started").count(),
        "in_progress": tasks.filter(status="In Progress").count(),
    }

    

    return render(request, "dashboard.html", {
        "tasks": tasks,
        "stats": stats,
        "filter":filters
    })


def start_task(request, pk):
    task = Task.objects.get(pk=pk)
    task.status = "In Progress"
    task.started_at = timezone.now()
    task.save()
    return redirect("dashboard")


def complete_task(request, pk):
    task = Task.objects.get(pk=pk)
    task.status = "Completed"
    task.completed_at = timezone.now()
    task.save()
    return redirect("dashboard")


def delete_task(request, pk):
    Task.objects.get(pk=pk).delete()
    return redirect("dashboard")

def export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="todo_export.csv"'

    writer = csv.writer(response)
    writer.writerow(["task", "status", "created_at", "started_at", "completed_at"])

    for t in Task.objects.all():
        writer.writerow([
            t.task,
            t.status,
            t.created_at,
            t.started_at,
            t.completed_at
        ])

    return response

def import_csv(request):
    if request.method == "POST" and request.FILES.get("file"):
        rows = request.FILES["file"].read().decode("utf-8").splitlines()
        reader = csv.DictReader(rows)

        for row in reader:
            created_at = parse_datetime(row["created_at"])

            Task.objects.get_or_create(
                task=row["task"],
                created_at=created_at, 
                defaults={
                    "status": row["status"],
                    "started_at": parse_datetime(row["started_at"]) if row["started_at"] else None,
                    "completed_at": parse_datetime(row["completed_at"]) if row["completed_at"] else None,
                }
            )

    return redirect("dashboard")    


@login_required
def sync_google_sheet(request):
    SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    RANGE = "Sheet1!A2:G"

    service = get_sheet_service()
    sheet = service.spreadsheets()

    values = []

    tasks = Task.objects.all().order_by("position")

    for task in tasks:
        values.append([
            task.id,
            task.task,
            task.status,
            str(task.created_at),
            str(task.started_at or ""),
            str(task.completed_at or ""),
            task.position,
        ])

    # Clear old rows
    sheet.values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE
    ).execute()

    # Write fresh data
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    return redirect("dashboard")

@csrf_exempt
def update_task_order(request):
    if request.method == "POST":
        data = json.loads(request.body)

        for item in data:
            Task.objects.filter(id=item["id"]).update(position=item["position"])

        return JsonResponse({"status": "ok"})
