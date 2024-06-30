from flask import Blueprint


bp = Blueprint('deutsche',
               __name__,
               template_folder="templates",
               static_folder="static",
               )

from app.deutsche.routes import *
