from rest_framework import mixins, status
from rest_framework.generics import ListAPIView, RetrieveAPIView, GenericAPIView

from . import models
from . import serializers


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
