import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wiser-heat-api-v2",
    version="2.0.0",
    author="Mark Parker",
    author_email="msparker@sky.com",
    description="A simple API for controlling the Drayton Wiser Heating system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/msp1974/wiserheatapiv2",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
