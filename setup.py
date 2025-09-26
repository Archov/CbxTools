from setuptools import setup, find_packages

setup(
    name="cbxtools",
    version="1.0.0",
    description="Tools for working with comic book archives (CBZ/CBR)",
    author="Jacob",
    packages=find_packages(),
    install_requires=[
        "pillow",
        "rarfile",
        "py7zr",
    ],
    entry_points={
        "console_scripts": [
            "cbxtools=cbxtools.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
    python_requires=">=3.8",
)
