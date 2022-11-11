from bson import ObjectId
from django import forms
from django.core.exceptions import ValidationError

from .core.crypto import BaseCipher
from .models import AppMediaStorageModel

from . import pushes


class UploadAppMediaForm(forms.ModelForm):
    class Meta:
        model = AppMediaStorageModel
        exclude = model.deprecated_fields() + ["media_url", "post_filename"]

    def clean(self):
        # `media` type: django.core.files.uploadedfile:InMemoryUploadedFile
        media_data = self.cleaned_data["media"]

        self.cleaned_data["file_size"] = media_data.size
        self.cleaned_data["src_filename"] = media_data.name
        self.cleaned_data["key"] = ObjectId().__str__()
        self.cleaned_data["access_token"] = ObjectId().__str__()
        self.cleaned_data["check_sum"] = BaseCipher.crypt_md5(media_data.file.read())

        # 部分或全部字段引用模型的字段, 如果form中未显性声明为非必填, 则后续校验通不过，无法保存到数据库中
        self.errors.clear()
        return self.cleaned_data

    @classmethod
    def create_media(cls, data=None, files=None, **kwargs):
        using = kwargs.pop("using")
        service = pushes[using]

        form = cls(data, files=files, **kwargs)

        if form.is_valid():
            media_obj = form.save()

            media_file = files["media"]
            media_file.seek(0)
            resp = service.upload_media(data["media_type"], media_file=media_file)

            if resp.get("errcode") != 0:
                media_obj.delete()
                raise ValidationError("Upload to %s media error:%s" % (using, resp.get("errmsg")))

            media_obj.media_id = resp["media_id"]
            media_obj.expire_time = service.get_expire_time(resp.get("created_at", 0))
            media_obj.save()

            return media_obj

        raise ValidationError("create_media error:%s" % form.errors)

