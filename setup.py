from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in novacept_blaster/__init__.py
from novacept_blaster import __version__ as version

setup(
	name="novacept_blaster",
	version=version,
	description="Social Media and Email Campaigning",
	author="Novacept",
	author_email="info@novacept.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
