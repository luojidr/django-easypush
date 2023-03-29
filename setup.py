import codecs
import os.path
from setuptools import setup, find_packages


NAME = "easypush"


def load_requirements(filename):
    reqs = []
    req_path = os.path.join(os.getcwd(), 'requirements', filename)

    with open(req_path, encoding="utf-8") as fp:
        for line in fp:
            if line.startswith('#') or not line.strip():
                continue

            pkg = line.split('#', 1)[0].strip()
            reqs.append(pkg)

    return reqs


if os.path.exists('README.md'):
    long_description = codecs.open('README.md', 'r', 'utf-8').read()
else:
    long_description = f'See http://pypi.python.org/pypi/{NAME}'


setup(
    name='django-easypush',
    license='MIT',
    version='1.1.3',
    maintainer="luojidr",
    maintainer_email='luojidr@163.com',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Intended Audience :: Developers",
    ],
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    url='https://github.com/luojidr/django-easypush',
    author='luojidr',
    author_email='luojidr@163.com',
    description='集成钉钉、企业微信的企业内部应用消息推送系统（支持MQ异步推送）',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=load_requirements("base.txt"),  # 所依赖的包
    python_requires=">=3.8",
)
