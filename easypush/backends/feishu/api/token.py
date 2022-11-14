from functools import partial
from datetime import datetime

from easypush.utils.exceptions import TokenError
from easypush.utils.constants import FeishuTokenTypeEnum as TokenEnum


class FeishuAccessToken:
    EXPIRE_TIME = 2 * 60 * 60

    def __init__(self, client, token_type=None, **kwargs):
        self._client = client
        self._app_id = client._app_key
        self._app_secret = client._app_secret

        self._token_mapping = {}
        self._token_type = token_type or TokenEnum.INTERNAL_TENANT.type
        self._tenant_key = kwargs.get("tenant_key")  # 商店应用 tenant_access_token 需要

        headers = {"Content-Type": "application/json; charset=utf-8"}
        self._top_request = partial(self._client._request, headers=headers)

    def get_token_type(self):
        return self._token_type

    def set_token_type(self, val):
        self._token_type = val

    token_type = property(get_token_type, set_token_type)

    @property
    def access_key(self):
        if self._token_type in [TokenEnum.INTERNAL_APP.type, TokenEnum.SHOP_APP.type]:
            return "app_access_token"
        elif self._token_type in [TokenEnum.INTERNAL_TENANT.type, TokenEnum.SHOP_TENANT.type]:
            return "tenant_access_token"
        else:
            raise TokenError("token type error")

    def get_access_token(self):
        """
        访问凭证类型	            是否需要用户授权	是否需要租户管理员授权	适用的应用场景
        app_access_token	        不需要	        不需要	            纯后台服务等
        tenant_access_token	        不需要	        需要	            网页应用、机器人、纯后台服务等
        user_access_token	        需要	        不需要	            小程序、网页应用等

        Data:
            {
                "code": 0,
                "msg": "success",
                "tenant_access_token": "a-6U1SbDiM6XIH2DcTCPyeub",
                # "app_access_token": "a-6U1SbDiM6XIH2DcTCPyeub",
                "expire": 7140
            }
        """
        token_enum = TokenEnum.get_token_enum(self._token_type)
        data = dict(app_id=self._app_id, app_secret=self._app_secret)

        if token_enum is None:
            raise TokenError("feishu access token type error")

        if token_enum.type == TokenEnum.SHOP_APP.type:
            app_ticket = self.get_app_ticket()
            data["app_ticket"] = app_ticket
        elif token_enum.type == TokenEnum.SHOP_TENANT.type:
            fs_token = FeishuAccessToken(client=self._client, token_type=TokenEnum.SHOP_APP.type)
            app_access_token = fs_token.get_access_token()[fs_token.access_key]
            data = dict(app_access_token=app_access_token, tenant_key=self._tenant_key)

        return self._top_request(method="POST", endpoint=token_enum.endpoint, data=data)

    def get_app_ticket(self):
        return self._top_request(
            method="POST",
            endpoint="auth.v3.app_ticket.resend",
            data=dict(app_id=self._app_id, app_secret=self._app_secret)
        )
