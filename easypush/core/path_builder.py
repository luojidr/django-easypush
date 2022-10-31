import os.path
import random
import string
import logging

from bson import ObjectId
from django.conf import settings
from django.urls import reverse
from django.utils.deconstruct import deconstructible

logger = logging.getLogger('django')


@deconstructible
class PathBuilder:
    def __init__(self, field_name, **kwargs):
        self._field_name = field_name
        self._kwargs = kwargs

        self._bucket_name = None
        self._bucket_capacity = 256
        self._per_bucket_size = 2000
        self._max_bucket_size = self._bucket_capacity * self._per_bucket_size

    @property
    def bucket_name(self):
        if self._bucket_name is not None:
            return self._bucket_name

        # easy_conf = settings.EASYPUSH["default"]["BACKEND"]
        self._bucket_name = "app_media"
        return self._bucket_name

    def __call__(self, media_instance, filename):
        media_root = settings.MEDIA_ROOT
        media_path = "".join([random.choice("0123456789abcdef") for _ in range(2)])

        ok_count = 0
        storage_media_path = None
        try_times = self._bucket_capacity
        src_fn, ext = os.path.splitext(filename)  # 文件后缀

        while ok_count < try_times:
            storage_media_path = os.path.join(media_root, self.bucket_name, media_path)
            if not os.path.exists(storage_media_path):
                os.makedirs(storage_media_path)

            filename_list = [
                fn for fn in os.listdir(storage_media_path)
                if os.path.isfile(os.path.join(storage_media_path, fn))
            ]

            try:
                if len(filename_list) > self._per_bucket_size:
                    logger.warning("[%s] 目录下已到达存储个数: %s" % (storage_media_path, self._per_bucket_size))

                # 保证重命名后的文件名的唯一性
                post_name = "".join(random.choices(string.ascii_letters, k=8)) + "_" + str(ObjectId())
                media_instance.post_filename = post_filename = post_name + ext

                media_name = media_instance.key + ext
                media_instance.media_url = reverse(viewname="media_preview", kwargs=dict(key=media_name))

                # The start position cannot be '/' with media path's to django 3.1.14
                # raise SuspiciousFileOperation(
                # django.core.exceptions.SuspiciousFileOperation:
                # Detected path traversal attempt in '/data/media/ding_media/8e/IpxcdlQw_630c7c192209b5c5d.jpg'
                full_media_path = os.path.join(storage_media_path, post_filename)      # 保存文件的实际路径

                if full_media_path[0] == "/" and full_media_path.startswith(media_root):
                    return full_media_path[len(media_root):]
                else:
                    return full_media_path
            except FileExistsError:
                ok_count += 1

        raise FileExistsError("Bucket: %s 已达到最大存储上限: %s" % (storage_media_path, self._bucket_max_size))




