from django.urls import path
from .views import dashboard, start_task, complete_task, delete_task , export_csv,import_csv, login_view,logout_view,update_task_order,sync_google_sheet,update_task,import_from_google_sheet

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("start/<int:pk>/", start_task, name="start_task"),
    path("complete/<int:pk>/", complete_task, name="complete_task"),
    path("delete/<int:pk>/", delete_task, name="delete_task"),
    path("export/", export_csv, name="export_csv"),
    path("import/", import_csv, name="import_csv"),
    path("reorder/", update_task_order, name="update_task_order"),
    path("sync-sheet/", sync_google_sheet, name="sync_google_sheet"),
    path("update_task/<int:task_id>/", update_task, name="update_task"),
    path("import_sheet/", import_from_google_sheet, name="import_from_google_sheet"),

]
