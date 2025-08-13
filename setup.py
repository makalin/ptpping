#!/usr/bin/env python3
"""
Setup script for PTPPing.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ptpping",
    version="1.0.0",
    author="PTPing Authors",
    author_email="authors@ptping.org",
    description="Network-wide Audio Latency Probe using PTP timing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/makalin/ptpping",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.12.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "ptpping=ptpping.ptpping:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ptpping": [
            "dashboard/templates/*.json",
            "generator/*.wav",
        ],
    },
)
