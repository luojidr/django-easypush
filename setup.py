from setuptools import setup


setup(
    name='easypush',
    license='Apache License 2.0',
    version='1.0.0',
    packages=['django-easypush'],
    zip_safe=False,
    include_package_data=True,
    url='https://github.com/luojidr/django-easypush',
    author='luoji',
    author_email='luojidr@163.com',
    description='继承钉钉、企业微信、飞书的应用消息，短信、邮件的消息推送系统',
    install_requires=[],  # 所依赖的包
)
