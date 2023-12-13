import io
from setuptools import setup, find_packages

with io.open("README.md", "r", encoding='utf-8') as f:
    long_description = f.read()

# Package metadata
NAME = 'vines_worker_sdk'
VERSION = '0.0.12'
DESCRIPTION = 'Vines Python 训练项目 SDK （供内部使用）'
AUTHOR = 'infmonkeys'
EMAIL = 'def@infmonkeys.com'
URL = 'https://github.com/inf-monkeys/vines-worker-sdk'
LICENSE = 'MIT'

# Required packages
INSTALL_REQUIRES = [
    "boto3",
    "botocore",
    "flask",
    "sentry_sdk",
    "sentry-sdk[flask]",
    "bullmq",
    "pyjwt",
    "redis"
]

# Packages to include
PACKAGES = find_packages()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    license=LICENSE,
    packages=PACKAGES,
    install_requires=INSTALL_REQUIRES,
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
