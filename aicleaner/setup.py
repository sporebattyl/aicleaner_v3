#!/usr/bin/env python3
"""
Setup script for AICleaner V3.
This script facilitates easy installation and setup of the AICleaner package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
version = {}
with open("src/__init__.py") as f:
    exec(f.read(), version)

# Read long description from README
long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="aicleaner",
    version=version.get("__version__", "3.0.0"),
    author="AICleaner Team",
    author_email="support@aicleaner.dev",
    description="Advanced AI-powered content analysis and management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aicleaner/aicleaner",
    project_urls={
        "Bug Tracker": "https://github.com/aicleaner/aicleaner/issues",
        "Documentation": "https://docs.aicleaner.dev",
        "Source": "https://github.com/aicleaner/aicleaner",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop", 
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Graphics",
        "Topic :: System :: Archiving",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0.0,<3.0.0",
        "aiohttp>=3.8.0,<4.0.0",
        "PyYAML>=6.0,<7.0.0",
        "asyncio-mqtt>=0.16.0,<1.0.0",
        "httpx>=0.25.0,<1.0.0",
        "paho-mqtt>=2.0.0,<3.0.0",
        "opencv-python>=4.8.0,<5.0.0",
        "Pillow>=10.0.0,<11.0.0",
        "numpy>=1.24.0,<2.0.0",
        "psutil>=5.9.0,<6.0.0",
        "google-generativeai>=0.5.0,<1.0.0",
        "python-dotenv>=1.0.0,<2.0.0",
        "structlog>=23.2.0,<24.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0,<8.0.0",
            "pytest-asyncio>=0.21.0,<1.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "black>=23.0.0,<24.0.0",
            "mypy>=1.5.0,<2.0.0",
            "flake8>=6.0.0,<7.0.0",
            "pre-commit>=3.5.0,<4.0.0",
        ],
        "enhanced": [
            "requests>=2.31.0,<3.0.0",
            "tenacity>=8.2.0,<9.0.0", 
            "cryptography>=41.0.0,<42.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aicleaner=aicleaner.src.main:main",
            "aicleaner-health=aicleaner.src.core.health:main",
        ],
    },
    include_package_data=True,
    package_data={
        "aicleaner": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
)