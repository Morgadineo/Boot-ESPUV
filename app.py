import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from app.models import *

@app.shell_context_processor
def make_shell_context():
    return {
            'sa': sa,
            'db': db,
            'User': User,
            'Post': Post,
            'Arduino': Arduino,
            'Location': Location,
            'UVRegister': UVRegister,
            'Category': Category,
            'Components': Components,
            'Arduino_Components': Arduino_Components,
        }

