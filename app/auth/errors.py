class UserAlreadyExist(Exception):
    def __init__(self, msg, category):
        self.msg = msg
        self.category = category
