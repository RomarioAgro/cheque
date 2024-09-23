from setuptools import setup, find_packages

NAME = "podeli-python"
VERSION = "0.0.1"
REQUIRES = ["urllib3 >= 1.26", "requests >= 2.28"]
setup(
    name=NAME,
    version=VERSION,
    description="",
    author_email="",
    url="",
    keywords=["podeli", "bnpl"],
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    long_description="""\
      Podeli BNPL Client
    """
)