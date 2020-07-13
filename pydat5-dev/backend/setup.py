from setuptools import find_namespace_packages, setup

setup(
    name="pydat",
    version="5.0.0",
    packages=find_namespace_packages(include=['pydat.*']),
    include_package_data=True,
    zip_safe=False,
    install_requires=["flask"],
    classifiers=["Programming language :: Python :: 3", ],
    python_requires=">=3.6",
)
