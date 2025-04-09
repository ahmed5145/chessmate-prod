#!/usr/bin/env python
"""
ChessMate project setup.

This setup.py file allows installing the ChessMate package
in development mode with pip install -e .
"""

from setuptools import find_packages, setup  # type: ignore

setup(
    name="chess_mate",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "django>=4.0,<5.0",
        "djangorestframework>=3.13.0",
        "python-dotenv>=0.19.0",
        "psycopg2-binary>=2.9.0",
        "django-cors-headers>=3.10.0",
        "djangorestframework-simplejwt>=5.0.0",
        "redis>=4.0.0",
        "celery>=5.2.0",
        "requests>=2.26.0",
        "django-debug-toolbar>=4.0.0",
        "python-json-logger>=2.0.0",
    ],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "mypy",
            "pytest",
            "pytest-django",
            "pytest-cov",
            "types-setuptools",
            "types-requests",
            "django-stubs",
            "djangorestframework-stubs",
            "pre-commit",
        ],
        "prod": [
            "gunicorn",
            "sentry-sdk",
            "django-storages",
            "whitenoise",
        ],
        "windows": [
            "pywin32",
            "eventlet",
        ]
    },
    python_requires=">=3.8",
    author="ChessMate Team",
    author_email="info@chessmate.com",
    description="A chess analysis and improvement platform",
    url="https://chessmate.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
