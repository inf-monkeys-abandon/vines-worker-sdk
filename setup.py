from setuptools import setup, find_packages

# Package metadata
NAME = 'vines_infer_sdk'
VERSION = '0.0.1'
DESCRIPTION = 'Vines Python 训练项目 SDK （供内部使用）'
AUTHOR = 'infmonkeys'
EMAIL = 'def@infmonkeys.com'
URL = 'https://github.com/inf-monkeys/viens-infer-helpers'
LICENSE = 'MIT'

# Required packages
INSTALL_REQUIRES = [
    # List your dependencies here, e.g., 'numpy', 'requests', 'matplotlib'
]

# Packages to include
PACKAGES = find_packages()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
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
