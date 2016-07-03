# Deployment

The application is currently deployed on a *Debian 8.3 x64* VPS. This documentation will reflect that. I am not a system administrator and cannot make assumptions about other operating systems.

## System dependencies.

To install all system dependencies run the following. This requires root/sudo permissions.

```
apt-get update && apt-get upgrade

apt-get install libffi-dev build-essential git sudo postgresql-9.4 postgresql-client-9.4 libpq-dev python-dev sudo
```

Next up install *pip*, the Python package manager by downloading the install script and running it with Python.

```
wget -O - https://bootstrap.pypa.io/get-pip.py | python
```

## Creating a new user

Running everything as root is a bad idea so create a new user.

```
adduser misofome
```

Add this user to the sudo list following this https://www.digitalocean.com/community/tutorials/how-to-add-and-delete-users-on-an-ubuntu-14-04-vps

Generate ssh keys on your own machine and place them in the `~/.ssh/authorized_keys` file (create it if necessary so we can ssh into that user. Also disable root login for added security.

Now we want to create our database.

## Setting up the database

```
su - postgres
createuser misofome
createdb misofome_prod
psql -d misofome_prod
```

we're in the psql shell now. We will change some settings and give the misofome user all privileges over the database.

```
ALTER DATABASE misofome_prod SET default_text_search_config TO 'dutch;'
ALTER USER misofome WITH password {password};
GRANT ALL privileges ON DATABASE misofome_prod TO misofome;
\q
```

## Installing the API.

Clone the github repo, or copy the files onto the server. Install *virtualenv* with pip by running `pip install --user virtualenv`. Create a virtualenv for this application in the project folder, my personal convention is to call it *venv*. Run `virtualenv venv`. A virtualenv creates a sandbox environment that we will use to install dependencies.

Activate the virtualenv by running `. venv/bin/activate` (note the leading dot it's important).

Now install the API by running `pip install -r requirements.txt`.

For initializing the database we will need two environmental variables, a key for ID generation and the database location/credentials. To generate the first run the following command and export the result

```
python -c 'import config; c = config.Config(); print c.find_coprime()'
SOME_NUMBER
export SOME_NUMBER
```

The postgres location/credentials string has the following format. Export it.

```
export postgresql://{user}:{pw}@localhost:5432/misofome_prod
```

Now you can run `app --config production db create fill`. And it will fill up the database.

Deactivate the virtualenv by runnning `deactivate`.

## Serving the application.

Install uwsgi by running `pip install --user uwsgi`. Next modify the *misofome_example.service* file by filling in the postgres location/credentials, a salt for the public facing hash ids, a secret key for the generation of user tokens and the previously generated key for the OBSCURE_ID_KEY. Rename it to misofome.service.

Place the service file in `/etc/systemd/system/` and run `sudo systemctl start misofome`. For more information on managing systemd services see https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units.

Next up take the misofome_example_nginx file and fill in the hostname or ipadress where you are hosting this application. Rename to misofome and place it in `/etc/nginx/sites-available`. Remove the file `/etc/nginx/sites-enabled/default` and symlink the misofome config file by running `ln -s /etc/nginx/sites-available/misofome /etc/nginx/sites-enabled/misofome`.

Run `sudo service nginx restart` and the api should be running on your domain.
