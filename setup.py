"""Setup script for PDF2Docs CLI tool."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding="utf-8").strip().split("\n")
    requirements = [req for req in requirements if req and not req.startswith("#")]

setup(
    name="pdf2docs",
    version="1.0.0",
    author="PDF2Docs",
    author_email="developer@pdf2docs.com",
    description="PDF to Text/Markdown CLI Tool using Docling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/pdf2docs",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing",
        "Topic :: Utilities",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pdf2docs=pdf2docs.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pdf2docs": ["*.yaml", "*.yml"],
    },
    keywords="pdf text markdown conversion docling cli",
    project_urls={
        "Bug Reports": "https://github.com/yourorg/pdf2docs/issues",
        "Source": "https://github.com/yourorg/pdf2docs",
    },
)