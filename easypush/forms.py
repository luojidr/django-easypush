from bson import ObjectId
from django import forms

from .core.crypto import BaseCipher
from .models import AppMediaStorageModel


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

