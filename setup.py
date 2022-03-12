import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="xcomfort",
    version="0.0.14",
    author="Jan Kristian Bjerke",
    author_email="jan.bjerke@gmail.com",
    description="Integration with Eaton xComfort Bridge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jankrib/xcomfort-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
    ],
    python_requires='>=3.7',
    install_requires=[
        "aiohttp",
        "rx",
        "pycryptodome"
    ],
)
