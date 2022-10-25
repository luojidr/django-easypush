import datetime

from django.db import models
from django.utils import timezone

from django.db.models.base import ModelBase
from django.db.models.options import Options
from django.utils.deconstruct import deconstructible

from ...core.globals import local_user


@deconstructible
class AutoExecutor:
    def __init__(self):
        pass

    def __call__(self, *args, **kwargs):
        try:
            login_user = local_user

            if login_user:
                return login_user.mobile

            return ""
        except RuntimeError:
            return "sys"


class BaseAbstractModel(models.Model):
    """ BaseModel """

    creator = models.CharField(verbose_name="创建人", max_length=200, default=AutoExecutor())
    modifier = models.CharField(verbose_name="创建人", max_length=200, default=AutoExecutor())
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    is_del = models.BooleanField(verbose_name='是否删除', default=False)

    class Meta:
        abstract = True
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        if not self.create_time:
            self.create_time = timezone.now()
        self.update_time = timezone.now()

        return super(BaseAbstractModel, self).save(*args, **kwargs)

    def save_attributes(self, force_update=False, **kwargs):
        for attr, value in kwargs.items():
            self.__dict__[attr] = value

        if force_update:
            self.save()

        return self

    def to_dict(self, *extra, exclude=()):
        fields = list(set(self.fields() + list(extra)) - set(exclude))
        # model_dict = model_to_dict(self)
        return {_field: self.default(self.__dict__[_field]) for _field in fields}

    @classmethod
    def fields(cls, exclude=()):
        """ Only obtain fields of BaseAbstractModel
         fields:
            cls._meta.get_fields()
         """
        fields = []
        exclude_fields = set(exclude)
        base_meta = BaseAbstractModel._meta
        base_fields_names = [_field.name for _field in base_meta.fields]

        for field in cls._meta.fields:
            field_name = field.attname

            if field_name in exclude_fields:
                continue

            if field_name not in base_fields_names:
                fields.append(field_name)

        return fields

    @classmethod
    def create_object(cls, force_insert=True, **kwargs):
        """ 创建对象 """
        model_fields = cls.fields()
        new_kwargs = {key: value for key, value in kwargs.items() if key in model_fields}

        if force_insert:
            obj = cls.objects.create(**new_kwargs)
        else:
            obj = cls(**new_kwargs)

        return obj

    @classmethod
    def deprecated_fields(cls):
        return [_field.name for _field in BaseAbstractModel._meta.fields]

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(o, datetime.date):
            return o.strftime("%Y-%m-%d")

        return o

    @classmethod
    def get_shard(cls, sharding_table):
        """ 分表，适用于获取历史数据(相同表中数据量太大，数据保存到其他表中，表结构完全相同) """
        return ShardingModel(shard_model_cls=cls).create_sharding_model(sharding_table)


class ShardingModel:
    """ ShardingModel support table horizontal partition """
    _shard_db_models = {}
    _base_shard_model_cls = None

    def __new__(cls,  *args, **kwargs):
        cls._base_shard_model_cls = kwargs.pop("shard_model_cls")
        return super().__new__(cls, *args, **kwargs)

    def create_sharding_model(self, sharding_table):
        class ShardMetaclass(ModelBase):
            def __new__(cls, name, bases, attrs):
                shard_model_cls = self._base_shard_model_cls
                base_model_name = shard_model_cls.__name__
                base_opts = shard_model_cls._meta
                manager_name = base_opts.default_manager.name

                concrete_fields = {field.name: field for field in base_opts.concrete_fields}
                base_attrs = {k: getattr(shard_model_cls, k) for k in dir(shard_model_cls) if not k.startswith('_')}
                base_attrs.update(concrete_fields)

                attrs.update({
                    '__module__': shard_model_cls.__module__,
                    '__doc__': 'Using %s table from %s Model' % (sharding_table, base_model_name),
                    "objects": base_opts.managers_map[manager_name],
                    'Meta': Options(base_opts, base_opts.app_label)
                }, **base_attrs)

                new_cls_name = "%sModel" % sharding_table.title().replace("_", "")
                model_cls = super().__new__(cls, new_cls_name, shard_model_cls.__bases__, attrs)
                model_meta = model_cls._meta
                model_meta.db_table = sharding_table  # Core

                verbose = " sharding(%s)" % sharding_table
                model_meta.verbose_name = base_opts.verbose_name + verbose
                model_meta.verbose_name_plural = base_opts.verbose_name_plural + verbose

                return model_cls

        class ProxyShardingModel(metaclass=ShardMetaclass):
            pass

        model_class = self._shard_db_models.get(sharding_table)
        if model_class is not None:
            return model_class

        # 这种方法只需要修改原Model类的_meta.db_table属性，缺点：无法同时使用多个分表，只能只有一个表有效
        # model_class = self._base_shard_model_cls._meta.db_table = sharding_table

        # 每次生成新的Model代理类，每个id(model_class)不同，互不影响
        model_class = ProxyShardingModel
        self._shard_db_models[sharding_table] = model_class
        return model_class

