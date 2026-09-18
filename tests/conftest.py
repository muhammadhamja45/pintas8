"""Test fixtures. Uses a throwaway PostgreSQL database built from database.sql."""
import io
import os
import sys

import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import BookType, Role, User  # noqa: E402

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_DB = "book_management_2_test"
ADMIN_DSN = dict(host="127.0.0.1", port=5432, user="postgres", password="root",
                 dbname="postgres")
PASSWORD = "password123"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://postgres:root@127.0.0.1:5432/{TEST_DB}")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "tests", "_uploads")
    WTF_CSRF_ENABLED = False


def _recreate_database():
    conn = psycopg2.connect(**ADMIN_DSN)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()", (TEST_DB,))
    cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    cur.close()
    conn.close()

    schema = io.open(os.path.join(BASE_DIR, "database.sql"), encoding="utf-8").read()
    conn = psycopg2.connect(**dict(ADMIN_DSN, dbname=TEST_DB))
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(schema)
    cur.close()
    conn.close()


@pytest.fixture(scope="session")
def app():
    _recreate_database()
    os.makedirs(TestConfig.UPLOAD_FOLDER, exist_ok=True)
    application = create_app(TestConfig)
    with application.app_context():
        # Reset the seeded hashes so tests know the password regardless of how
        # database.sql was generated.
        for user in User.query.all():
            user.set_password(PASSWORD)
        db.session.commit()
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


def csrf_for(client):
    """Load the login page like a browser would and read its CSRF meta tag."""
    html = client.get("/login").get_data(as_text=True)
    marker = 'name="csrf-token" content="'
    start = html.index(marker) + len(marker)
    return html[start:html.index('"', start)]


def login(client, identity, password=PASSWORD):
    token = csrf_for(client)
    res = client.post("/api/auth/login",
                      json={"identity": identity, "password": password},
                      headers={"X-CSRF-Token": token})
    # A successful login rotates the session, so refresh the client's token.
    if res.status_code == 200:
        client.environ_base["HTTP_X_CSRF_TOKEN"] = res.get_json()["data"]["csrf_token"]
    else:
        client.environ_base["HTTP_X_CSRF_TOKEN"] = token
    return res


@pytest.fixture()
def as_user(client):
    login(client, "user@example.com")
    return client


@pytest.fixture()
def book_type_id(app):
    with app.app_context():
        return BookType.query.filter_by(is_active=True).order_by(BookType.id).first().id


def client_for(app, identity):
    """A separate test client logged in as the given account."""
    new_client = app.test_client()
    login(new_client, identity)
    return new_client
