from setuptools import setup, find_packages


setup(
    name='django-easypush',
    license='MIT',
    version='1.0.0',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Intended Audience :: Developers",
    ],
    packages=find_packages(exclude=["*.demo"]),
    zip_safe=False,
    include_package_data=True,
    url='https://github.com/luojidr/django-easypush',
    author='luoji',
    author_email='luojidr@163.com',
    description='集成钉钉、企业微信、飞书的应用消息，短信、邮件的消息推送系统',
    install_requires=[
        "django>=4.1",
        "werkzeug==2.2.2",
        "dingtalk-sdk==1.3.8",
    ],  # 所依赖的包
)
