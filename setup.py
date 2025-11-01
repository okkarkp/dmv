from setuptools import setup, find_packages

setup(
    name="dmw_validator",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "dmw_validator": [
            "config.json",
            "models/*.gguf"
        ]
    },
    install_requires=[
        "pandas",
        "openpyxl",
        "llama-cpp-python",
    ],
    entry_points={
        "console_scripts": [
            "dmw-validator = dmw_validator.cli:main",
        ],
    },
)
