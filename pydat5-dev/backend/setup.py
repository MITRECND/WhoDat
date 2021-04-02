from setuptools import find_namespace_packages, setup

setup(
    name="pydat",
    version="5.0.0",
    packages=find_namespace_packages(include=['pydat.*']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "flask",
        "cerberus",
        # Defaults to 7, but should allow for 6 if pre-installed
        "elasticsearch>=6.0.0,<8.0.0",
        "ply",
        "flask-caching",
        "requests"
        ],
    tests_require=[
        "pytest",
        "pytest-cov",
        "flake8",
        "blinker"
    ],
    classifiers=["Programming language :: Python :: 3", ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "pydat-dev-server = pydat.scripts.api:main",
            "pydat-populator = pydat.scripts.elasticsearch_populate:main"
        ]
    },
)
