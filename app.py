from os import environ
from website.app import create_app

app = create_app({
    'SECRET_KEY': 'secret',
    'OAUTH2_REFRESH_TOKEN_GENERATOR': True,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_DATABASE_URI': environ.get("DATABASE_URL", "sqlite:///db.sqlite"),
})
