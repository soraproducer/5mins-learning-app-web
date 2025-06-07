from setuptools import setup, find_packages

setup(
    name="5mins-learning-app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi[all]",
        "sqlalchemy[asyncio]",
        "asyncpg",
        "openai>=1.0",
        "anthropic>=0.4",
        "sse-starlette",
        "httpx",
        "pytest-asyncio",
        "python-dotenv",
        "pydantic>=2.0",
        "pytest",
        "requests",
        "aiosqlite",  # For SQLite in tests
    ],
)
