"""
Database module for SiliconFlow I2V Generator.
"""

import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """Get a database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db(app):
    """Initialize the database."""
    with app.app_context():
        db = get_db()

        # Create tables
        db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                message TEXT,
                image_path TEXT,
                prompt TEXT,
                request_id TEXT,
                video_path TEXT,
                model TEXT,
                vlm_model TEXT,
                llm_model TEXT,
                prompt_template TEXT,
                parent_task_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # Check if new columns exist, add them if they don't
        try:
            db.execute('SELECT vlm_model FROM tasks LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE tasks ADD COLUMN vlm_model TEXT')

        try:
            db.execute('SELECT llm_model FROM tasks LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE tasks ADD COLUMN llm_model TEXT')

        try:
            db.execute('SELECT parent_task_id FROM tasks LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE tasks ADD COLUMN parent_task_id TEXT')

        try:
            db.execute('SELECT prompt_template FROM tasks LIMIT 1')
        except sqlite3.OperationalError:
            db.execute('ALTER TABLE tasks ADD COLUMN prompt_template TEXT')

        db.commit()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
