from setuptools import setup, find_packages

setup(
    name="fin-officer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "aiosmtplib",
        "aioimaplib",
        "sqlalchemy",
        "aiosqlite",
        "fastapi-utils",
        "python-dotenv",
        "email-validator",
        "requests",
        "aiohttp",
        "httpx",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "flake8",
            "pylint",
            "isort",
            "tox",
            "httpx",
        ],
    },
    python_requires=">=3.10",
)
