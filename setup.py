from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="discord-betting-bot",
    version="0.1.0",
    author="Your Company",
    author_email="sales@yourcompany.com",
    description="A commercial Discord bot for managing sports betting",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://yourcompany.com/betting-bot",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Communications :: Chat",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "betting-bot=bot.main:main",
        ],
    },
) 