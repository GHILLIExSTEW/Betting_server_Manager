from setuptools import setup, find_packages

setup(
    name="betting_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "python-dotenv",
        "aiohttp",
        "aiosqlite",
    ],
    python_requires=">=3.8",
) 