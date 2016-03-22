class AuthorizationError(Exception):
    def __init__(self, msg=None, status_code=401, *args, **kwargs):
        self.msg = msg or "Unauthorized request"
        self.status_code = status_code
        self.response = dict(status=self.status_code, message=self.msg)
        Exception.__init__(self, msg, *args, **kwargs)

    def __str__(self):
        return repr(self.msg)
