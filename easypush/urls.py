from django.conf import settings
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

    # Media File Storage
    re_path(r"^api/app/media/upload$", view=views.UploadAppMediaApi.as_view(), name="msg_media_upload"),

    # Preview Media File
    # eg: /media/preview/23664tfhituj.png?access_token=645rjhfds3kj
    re_path(
        "^%s/preview/(?P<key>.*?)$" % settings.MEDIA_URL.strip("/"),
        view=views.PreviewMediaFileApi.as_view(), name="media_preview"
    ),

    re_path(r"^api/app/media/list$", view=views.ListAppMediaApi.as_view(), name="app_media_list"),
    re_path(r"^api/app/message/list$", view=views.ListAppMessageApi.as_view(), name="app_message_list"),

    # Send app message
    re_path(r"^api/app/message/send$", view=views.SendAppMessageRecordApi.as_view(), name="send_message"),
]
