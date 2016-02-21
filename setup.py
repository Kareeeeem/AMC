import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='AMC',
    version='0.0.1',
    description='Backend for app to support the treatment of Misofonie.',
    long_description=read('README.md'),
    author='Mohammed Kareem',
    author_email='kareeeeem@gmail.com',
    license='MIT',
    # packages=find_packages(),
    packages=['app', 'scripts', 'tests'],
    install_requires=[
    ],
    entry_points="""
        [console_scripts]
        app=scripts.cli:cli
        lucidchart-erd=scripts.erd:cli
    """,
    include_package_data=True,
    zip_safe=False,
)
