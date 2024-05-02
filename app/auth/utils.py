from app.auth.errors import LoginFunctionUndefined
from flask import session, current_app, redirect, url_for
from functools import wraps


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not session['currentAgency']:
            if 'LOGIN_FUNCTION' in current_app.config:
                return redirect(url_for(current_app.config['LOGIN_FUNCTION']))
            raise LoginFunctionUndefined
        return func(*args, **kwargs)
    return decorated_view
