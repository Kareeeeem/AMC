class AuthorizationError(Exception):
    def __init__(self, msg=None, status_code=401, *args, **kwargs):
        self.msg = msg or "Unauthorized request"
        self.status_code = status_code
        self.response = dict(status=self.status_code, message=self.msg)
        Exception.__init__(self, msg, *args, **kwargs)

    def __str__(self):
        return repr(self.msg)


class PaginationError(Exception):
    def __init__(self, page, max_pages, per_page, *args, **kwargs):
        self.errors = []
        if page > 0:
            self.errors.append('Page %s out of range, collection has %s pages.' % (page, max_pages))
        if page < 1:
            self.errors.append('Pages start at 1.')
        if per_page > 100:
            self.errors.append('Max per_page is 100.')

        Exception.__init__(self, ' '.join(self.errors), *args, **kwargs)

    def __str__(self):
        return repr(self.msg)


class NoResultsError(Exception):
    pass
