import os
import setuptools


def readme() -> str:
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()


def get_version() -> str:
    with open("src/hedera_cli/_version.py", "r", encoding="utf-8") as fh:
        return fh.read().split('"')[1]


setuptools.setup(
    name="hedera-cli", # Replace with your own username
    version=get_version(),
    author="Wensheng Wang",
    author_email="wenshengwang@gmail.com",
    description="Hedera CLI in Python",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/wensheng/hedera-cli-py",
    project_urls={
        "Bug Tracker": "https://github.com/wensheng/hedera-cli-py/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=['hedera-sdk-py>=2.0.8',
                      'colorama>=0.4.4',
                      'python-dotenv>=0.18.0',
                      'requests>=2.19.1',
                      'getch>=1.0 ; platform_system!="Windows"'],
    python_requires=">=3.6",
    # include_package_data=True,
    # package_data={ "hedera-cli": ["*"]},
    entry_points={
        "console_scripts": ["hedera-cli=hedera_cli.main:main"]
    },
)
