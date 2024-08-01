from flask import Blueprint


bp = Blueprint('finapi',
               __name__,
               template_folder="templates",
               static_folder="static",
               )

from app.finapi.routes import *
