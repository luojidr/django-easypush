import logging
import os.path

from django.conf import settings
from django.views import View
from django.views.static import serve
from django.http.response import Http404
from django.core.exceptions import PermissionDenied

from rest_framework.views import APIView
from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView

from . import pushes
from . import forms, models, serializers
from .utils.decorators import exempt_view_csrf
from easypush.tasks.task_send_message import send_message_by_mq

logger = logging.getLogger("django")


# Platform application related interface class
class ListAppTokenPlatformApi(ListAPIView):
    serializer_class = serializers.AppTokenPlatformSerializer
    queryset = models.AppTokenPlatformModel.objects.filter(is_del=False).all()


class RetrieveAppTokenPlatformByAgentIdApi(RetrieveAPIView):
    lookup_field = "agent_id"

    queryset = models.AppTokenPlatformModel.objects.filter(is_del=False).all()
    serializer_class = serializers.AppTokenPlatformSerializer


class EditAppTokenPlatformApi(mixins.CreateModelMixin,
                              mixins.UpdateModelMixin,
                              GenericAPIView):
    serializer_class = serializers.AppTokenPlatformSerializer

    def get_object(self):
        agent_id = self.request.data["agent_id"]
        platform_type = self.request.data["platform_type"]
        return models.AppTokenPlatformModel.objects.get(agent_id=agent_id, platform_type=platform_type)

    def post(self, request, *args, **kwargs):
        """ Create or Update micro application """
        agent_id = request.data["agent_id"]
        platform_type = self.request.data["platform_type"]
        app_obj = models.AppTokenPlatformModel.objects.filter(agent_id=agent_id, platform_type=platform_type).first()

        if not app_obj:
            return self.create(request, *args, **kwargs)
        return self.update(request, *args, **kwargs)


@exempt_view_csrf
class PreviewMediaFileView(View):
    LOGIN_REQUIRED = False

    def get(self, request, *args, **kwargs):
        """ Preview file """
        key_name = kwargs["key"]
        access_token = request.GET.get("access_token")

        key, ext = os.path.splitext(key_name)
        media_obj = models.AppMediaStorageModel.get_media_by_key(key=key)

        if not media_obj:
            return Http404()

        if not media_obj.is_share and access_token != media_obj.access_token:
            raise PermissionDenied(403, "No permission tp preview")

        document_root, path = os.path.split(media_obj.media.path)
        return serve(request, path, document_root)


class UploadAppMediaApi(APIView):
    def post(self, request, *args, **kwargs):
        """  Upload message media files """
        data = request.data
        app_token = data.pop("app_token")[0]
        app_obj = models.AppTokenPlatformModel.get_app_by_token(app_token=app_token)
        using = app_obj.platform_type

        media_type = data.pop("media_type")[0]  # QueryDict => [image], [file], [voice]
        media_data = dict(data, media_title=data.get("media_title", ""), media_type=media_type, app=app_obj.id)
        media_obj = forms.UploadAppMediaForm.create_media(media_data, files=request.FILES, using=using)

        return Response(data=media_obj.to_dict(exclude=("media",)), status=status.HTTP_200_OK)


class ListAppMediaApi(ListAPIView):
    serializer_class = serializers.AppMediaStorageSerializer

    def get_queryset(self):
        query_params = self.request.query_params
        app_id = query_params.get("app_id")
        media_title = query_params.get("media_title")
        media_type = query_params.get("media_type")

        query_kwargs = dict(is_del=False)
        app_id and query_kwargs.update(app_id=app_id)
        media_type and query_kwargs.update(media_type=media_type)
        media_title and query_kwargs.update(media_title__contains=media_title)

        return models.AppMediaStorageModel.objects.filter(**query_kwargs).all()


class ListAppMessageApi(ListAPIView):
    serializer_class = serializers.AppMessageSerializer
    queryset = models.AppMessageModel.objects.filter(is_del=False).all()


class SendAppMessageRecordApi(GenericAPIView):
    serializer_class = serializers.AppMsgPushRecordSerializer

    def post(self, request, *args, **kwargs):
        """ Push app message according to `userid`
        request.data:
            app_token: string, must be present, app_token attribute of AppTokenPlatformModel instance
            msg_type： int, must be present, look up `QyWXMessageTypeEnum` and `DingTalkMessageTypeEnum` etc.
            msg_body_json: string, must be present, message body json
            receiver_mobile: string, receiver's mobile to send, eg: '13600000000,13500000001'
            receiver_userid: string, must be present, receiver's userid to send eg:'1602133682287,1635343667135'
            is_async: bool, default is true, if is_async is true, use mq to send message
            using: string, default is `default` Which backend push to send
        """
        self.serializer_class.async_send_mq(data=request.data, task_fun=send_message_by_mq)
        return Response(data=None, status=status.HTTP_200_OK)
