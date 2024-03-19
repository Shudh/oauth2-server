# app.py
import os
from os import environ
from website.app import create_app
environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'
environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


app = create_app({
    'SECRET_KEY': 'secret',
    'OAUTH2_REFRESH_TOKEN_GENERATOR': True,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_DATABASE_URI': environ.get("DATABASE_URL", "sqlite:///db.sqlite"),
})
