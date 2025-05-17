from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import registry

db = SQLAlchemy()
mapper_registry = registry()

def reflect_selected_tables(app):
    metadata = MetaData()
    with app.app_context():
        metadata.reflect(bind=db.engine, only=[
            'appuser',
            'role',
            'studyroom',
            'reservation',
            'asset',
            'resetreservation',
            'feedback',
            'maintenance',
            'policy',
            'adminlog'
        ])
        return metadata
