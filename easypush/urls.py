from django.urls import re_path, path
from . import views

urlpatterns = [
    # Platform application related interfaces
    re_path("^api/platform/app/edit$", view=views.EditAppTokenPlatformApi.as_view(), name="edit_app_platform"),
    re_path("^api/platform/app/list$", view=views.ListAppTokenPlatformApi.as_view(), name="list_app_platform"),
    re_path(
        r"^api/platform/app/agent_id/(?P<agent_id>\d+)/$",
        view=views.RetrieveAppTokenPlatformByAgentIdApi.as_view(),
        name="retrieve_app_platform_by_agentid"
    ),
]
