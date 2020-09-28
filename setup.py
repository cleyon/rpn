import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rpn-cleyon",
    version="15.7",
    author="Christopher Leyon",
    author_email="cleyon@gmail.com",
    description="RPN calculator and programming language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cleyon/rpn",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD 2-Clause License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
