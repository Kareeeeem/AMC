#AMC

Graduation project

#Deployment
Pull from github repo and run `cd amc; pip install -r requirements.txt`
Make sure Database credentials are available in the environment as
`SQLALCHEMY_DATABASE_URL`.

Further instructions for setting up the server with nginx and uswgi will
follow.

#Dev requirements
For all the development requirements run `pip -r dev_requirements.txt`.
This will install

* pgcli, A postres command line interface with autocomplete and syntax highlighting.
* pytest, A test library. Run tests with `py.test tests`
* ipython, A better python REPL with autocomplete and syntax highlighting.
* httpie, An easier subsitute for curl.

#System dependencies
Make super system dependencies are installed for
* psycopg2
* bcrypt

Make sure you install hstore extension on postgres. As pg superuser run
`psql application_db -c 'create extension hstore;'`

#Project structure
```
.
├── app
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── api.py
│   │       ├── auth.py
│   │       └── __init__.py
│   ├── __init__.py
│   ├── lib.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── meta
│   │   │   ├── columns.py
│   │   │   ├── __init__.py
│   │   │   ├── mixins.py
│   │   │   └── orm.py
│   │   └── models.py
│   └── serializers.py
├── config.py
├── dev_requirements.txt
├── env
├── MANIFEST.in
├── README.md
├── requirements.txt
├── scripts
│   ├── amisos.json
│   ├── cli.py
│   ├── db.py
│   ├── erd.py
│   ├── flask_app.py
│   └── __init__.py
├── setup.py
└── tests
    ├── __init__.py
    ├── test_obfuscate.py
    ├── test_password.py
    ├── test_with_app
    │   ├── amisos.json
    │   ├── conftest.py
    │   ├── __init__.py
    │   ├── test_auth.py
    │   ├── test_questionnaire.py
    │   └── test_with_config.py
    └── test_with_config.py

8 directories, 36 files
```
