import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:newpassword@localhost/LibraryEase'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'supersecretkey'
