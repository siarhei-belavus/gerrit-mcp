from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gerrit-mcp",
    version="0.1.1",
    author="Siarhei Belavus",
    author_email="siarhei_belavus@epam.com",
    description="A Model Context Protocol (MCP) server implementation for AI-powered Gerrit code reviews",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siarhei-belavus/gerrit-mcp",
    project_urls={
        "Bug Tracker": "https://github.com/siarhei-belavus/gerrit-mcp/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Review",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "aiohttp==3.9.3",
        "python-dotenv==1.0.1",
        "mcp-sdk==0.1.0"
    ],
    entry_points={
        "console_scripts": [
            "gerrit-mcp=src/mmcp/server:main"
        ]
    },
)