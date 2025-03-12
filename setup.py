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
        "patool",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
    python_requires=">=3.6",
)
