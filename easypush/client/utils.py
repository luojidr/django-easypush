from . import AppMessageHandler
from easypush.core.crypto import AESCipher
from easypush.models import AppTokenPlatformModel

push_backend_mapping = {}


def get_push_backend(app_id=None, instance=None):
    assert app_id is not None or instance is not None, "Not exist app object."

    global push_backend_mapping

    if app_id:
        instance = AppTokenPlatformModel.objects.get(id=app_id)

    app_token = instance.app_token
    app_md5 = AESCipher.crypt_md5(app_token)

    if app_md5 in push_backend_mapping:
        return push_backend_mapping[app_md5]

    push = AppMessageHandler(
        backend=instance.platform_type,
        corp_id=instance.corp_id, agent_id=instance.agent_id,
        app_key=instance.app_key, app_secret=instance.app_secret,
    )
    push_backend_mapping[app_md5] = push
    return push

