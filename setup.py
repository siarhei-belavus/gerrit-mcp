from setuptools import setup, find_packages

setup(
    name="gerrit_ai_review",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "gerrit-ai-review=server:main"
        ]
    },
    python_requires=">=3.8",
)