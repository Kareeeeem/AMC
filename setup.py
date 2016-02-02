import os
from setuptools import setup, find_packages


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
    packages=find_packages(),
    install_requires=[
        'click==6.2',
        'Flask==0.10.1',
        'marshmallow==2.5.0',
        'SQLAlchemy==1.0.11',
        'bcrypt==2.0.0',
        'psycopg2==2.6.1',
    ],
    entry_points="""
        [console_scripts]
        db=scripts.db:cli
    """,
    include_package_data=True,
    zip_safe=False,
)
