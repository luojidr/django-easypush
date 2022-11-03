import logging
import os.path

from django.conf import settings
from django.db import transaction
from django.views import View
from django.views.static import serve
from django.http.response import Http404
from django.core.exceptions import PermissionDenied, ValidationError

from rest_framework.views import APIView
from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView

from . import easypush
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
    MAX_MSG_SIZE_TO_MQ = 100
    MAX_MSG_BATCH_SIZE = 2000
    serializer_class = serializers.AppMsgPushRecordSerializer

    def async_send_messages(self, data):
        """ Asynchronously send messages : first save db, then send messages through mq

        :param data: dict or list of dictionary
        :return:
        """
        is_async = data.pop("is_async", True)

        # First to save message into db
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        message_body = dict(**data)

        # Split `receiver_userid`, Determine whether to send in batch
        receiver_userid = message_body.pop("receiver_userid", "")
        userid_list = [m.strip() for m in receiver_userid.split(",") if m.strip()]

        many = len(userid_list) > 1
        max_batch_size = self.MAX_MSG_BATCH_SIZE

        if many:
            if not userid_list:
                raise ValueError("Parameter `receiver_userid` not allowed empty")

            if len(receiver_userid) > max_batch_size:
                raise ValidationError("The number of `userid` exceeds the maximum limit(max:%s)" % max_batch_size)

            data_or_list = [dict(**message_body, receiver_userid=userid) for userid in userid_list]
        else:
            data_or_list = dict(message_body, receiver_userid=receiver_userid)

        # many=True: support batch to create.
        # If the create method(to batch creation) is not overridden in the `list_serializer_class` class
        # only-used `serializer_class` class, and the create method will be called to create one by one,
        # the efficiency is relatively low
        serializer = self.serializer_class(data=data_or_list, many=many)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance_list = instance if isinstance(instance, list) else [instance]

        # Second to asynchronously push messages  into MQ
        for i in range(0, len(instance_list), max_batch_size):
            slice_instances = instance_list[i: i + self.MAX_MSG_SIZE_TO_MQ]
            msg_uid_list = [msg_obj.msg_uid for msg_obj in slice_instances]

            if is_async:
                send_message_by_mq.delay(msg_uid_list=msg_uid_list)
            else:
                send_message_by_mq.run(msg_uid_list=msg_uid_list)

    def post(self, request, *args, **kwargs):
        """ Push app message according to `userid`
        request.data:
            app_token: string, app_token attribute of AppTokenPlatformModel instance
            msg_type： int, look up `QyWXMessageTypeEnum` and `DingTalkMessageTypeEnum` etc.
            msg_body_json: string, message body json
            receiver_mobile: string, receiver's mobile to send message, eg: '13600000000,13500000001'
            receiver_userid: string, receiver's userid to send message eg: '1602133682287,1635343667135'
            is_async: bool, default is false, if is_async is true, use mq to send message
            using: string, default is `default` Which backend push to send
        """
        self.async_send_messages(data=request.data)
        return Response(data=None, status=status.HTTP_200_OK)
