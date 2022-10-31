import logging
import os.path

from django.conf import settings
from django.db import transaction
from django.views import View
from django.views.static import serve
from django.http.response import Http404
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView

from . import easypush
from . import forms, models, serializers

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
        """ 添加或更新微应用 """
        agent_id = request.data["agent_id"]
        platform_type = self.request.data["platform_type"]
        app_obj = models.AppTokenPlatformModel.objects.filter(agent_id=agent_id, platform_type=platform_type).first()

        if not app_obj:
            return self.create(request, *args, **kwargs)
        return self.update(request, *args, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
class PreviewMediaFileApi(View):
    LOGIN_REQUIRED = False

    def get(self, request, *args, **kwargs):
        """ 文件预览 """
        key_name = kwargs["key"]
        access_token = request.GET.get("access_token")

        key, ext = os.path.splitext(key_name)
        media_obj = models.AppMediaStorageModel.get_media_by_key(key=key)

        if not media_obj:
            return Http404()

        if not media_obj.is_share and access_token != media_obj.access_token:
            raise PermissionDenied(403, "您没有权限访问")

        document_root, path = os.path.split(media_obj.media.path)
        return serve(request, path, document_root)


class UploadMessageMediaApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 上传消息媒体文件 """
        data = request.data
        app_token = data.pop("app_token")[0]
        app_obj = models.AppTokenPlatformModel.get_app_by_token(app_token=app_token)

        media_type = data.pop("media_type")[0]  # QueryDict => [image], [file], [voice]
        media_data = dict(data, media_title=data.get("media_title", ""), media_type=media_type, app=app_obj.id)
        form = forms.UploadAppMediaForm(media_data, files=request.FILES)
        if form.is_valid():
            with transaction.atomic():
                media_obj = form.save()
                file_obj = request.FILES["media"]

                if settings.DEBUG:
                    resp = dict(media_id="@debug_test")
                else:
                    resp = easypush.upload_media(media_type, media_file=file_obj)
                logger.info("UploadMessageMediaApi.upload_media debug:%s, ret: %s", settings.DEBUG, resp)

                media_obj.media_id = resp["media_id"]
                media_obj.save()

                return Response(data=media_obj.to_dict(exclude=("media",)), status=status.HTTP_200_OK)

        return Response(data=form.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListMessageMediaApi(ListAPIView):
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
