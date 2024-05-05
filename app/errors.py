class UserAlreadyExist(Exception):
    def __init__(self, msg, category):
        self.msg = msg
        self.category = category


class UserDoesntExist(Exception):
    def __init__(self, msg="User doesn't exist", category="danger"):
        self.msg = msg
        self.category = category


class LoginFunctionUndefined(Exception):
    msg = "login function was not defined in configrations of app"
    category = "danger"
