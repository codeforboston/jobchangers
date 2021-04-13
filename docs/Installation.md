# Installation

## Option 1 (easiest): Docker

Run all commands in the `stack` directory (`cd stack` from the root directory).

1. Install Docker and Docker Compose

   On Mac and Windows, the easiest way is to install [Docker Desktop](https://www.docker.com/products/docker-desktop)

   Or you can install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) directly.

2. Copy the `compose/.env.template` file to `compose/.env`. Replace the `SECRET_KEY` value with your Django key, and replace the `ONET_PASSWORD` with the O\*NET account password (ping the jobhopper channel if you don't know the password).

3. Build the Docker images by running `./dev build`. You will need to run this whenever the dependencies for the frontend or api change.

4. Start the app by running `./dev up`.

   You can start a shell in the Django container with `./dev shell api`, and a shell in the database container with `./dev shell db`.

   You can start `psql`, an interactive PostgreSQL shell, with `./dev psql`.

5. To run backend tests, once the container is running, this command will work in a new command window to execute the tests against the running API container:
   `./compose/dev-deployment exec api python manage.py test`

## Option 2: Clone and run

1. Install [Python 3.7](https://www.python.org/downloads/release/python-378/).

2. Install [virtualenv](https://pypi.org/project/virtualenv/) from `pip`:

   ```sh
   python3.7 -m pip install virtualenv

   OR on Windows

   python -m pip install virtualenv
   ```

3. Clone this repo to local:
   ```sh
   git clone https://github.com/codeforboston/jobhopper.git
   ```
4. Create a virtual environment of Python 3.7 in the root of the local repo:

   ```sh
   cd jobhopper
   python3.7 -m virtualenv --python=3.7 venv

   OR on Windows

   cd jobhopper
   python -m virtualenv --python=3.7 venv
   ```

5. Activate venv:

   ```sh
   . ./venv/bin/activate

   OR on Windows

   ./venv/Scripts/activate
   ```

6. Install project dependencies from `requirements.txt`:
   ```sh
   pip install -r requirements.txt
   ```
7. Create a personal `.env` file to include environment variables for the app:
   (Note: Don't include `.env` in commit, thus it's in `.gitignore`):

   ```sh
   SECRET_KEY='[generated key]'
   ```

   You can get your own 50 character secret key from [here](https://miniwebtool.com/django-secret-key-generator/).

8. Create PostgreSQL DB:

   a. Install [PostgreSQL 12](https://www.postgresql.org/download/)

   b. Start PostgreSQL service and check if clusters are running.

   ```sh
   sudo service postgresql start
   pg_lsclusters
   ```

   If the text is green, it's working.

   c. Run `psql` through the newly created `postgres` user.

   ```sh
   sudo -i -u postgres
   psql
   ```

   d. Create a new user/role for the site to access the database to. Name it
   however you like as long as you note the username and password for putting
   it in `.env`.

   ```sql
   CREATE ROLE [user]
   SUPERUSER
   LOGIN
   PASSWORD '[password]';
   ```

   e. Create a new database for the site to access. Name it however you like
   (preferably 'jobhopperdatabase') as long as you note the name of the
   database for putting it in `.env`.

   ```sql
   CREATE DATABASE [database name]
     WITH OWNER = [user];
   ```

   f. Exit out of `psql` and `postgres` user with the `exit` command for both
   cases.

   g. Add those information you written into the `.env` file.

   ```sh
   SECRET_KEY='[generated key]'

   DB_NAME='[database name]'
   DB_USER='[user/role name]'
   DB_PASSWORD='[password]'
   DB_HOST='127.0.0.1'  # Localhost IP
   ```

9. Migrate from `manage.py` in root.

   ```sh
   python manage.py migrate
   ```

10. Now run the server via this script:

    ```sh
    python manage.py runserver
    ```

11. Go to the URL `[baseurl]/jobs/api/leads/` and test out creating entries.
12. Go to the URL `[baseurl]/api/v1/health` and ensure it returns JSON data.
13. Go to the URL `[baseurl]/jobs` and ensure it returns data.
