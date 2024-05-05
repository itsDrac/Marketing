from flask import Blueprint

bp = Blueprint('lex',
               __name__,
               url_prefix="/lex",
               template_folder="templates",
               static_folder="static",
               )

from app.auth.routes import *
