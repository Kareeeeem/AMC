import math

from flask import url_for
from utils import merge_sqla_results


class Pagination(object):
    def __init__(self, request, query=None):
        # the query_params multidict is immutable so make a copy of it.
        self.query_params = request.args.copy()

        # the arguments passed to a route, such as an id (not the query params)
        self.view_args = request.view_args

        # the endpoint, such as v1.users
        self.endpoint = request.url_rule.endpoint

        # pop the original pagination params and save them.
        self.page = int(self.query_params.pop('page', 1))
        self.per_page = int(self.query_params.pop('per_page', 10))

        self.total_count = query.count()

        if self.page < 1 or self.page > self.pages or self.per_page > 100:
            raise PaginationError(self)

        query_results = query.offset(self.offset).limit(self.limit).all()
        self.items = merge_sqla_results(query_results)

    def generate_url(self, **pagination_params):
        param_dicts = (pagination_params,
                       self.view_args,
                       self.query_params.to_dict(flat=False))
        # combine all these dicts
        params = reduce(lambda a, b: dict(a, **b), param_dicts)
        return url_for(self.endpoint, _external=True, **params)

    @property
    def pages(self):
        pages = int(math.ceil(self.total_count / float(self.per_page)))
        return pages or 1

    @property
    def first_page_url(self):
        return self.generate_url(page=1, per_page=self.per_page)

    @property
    def last_page_url(self):
        return self.generate_url(page=self.pages, per_page=self.per_page)

    @property
    def current_page_url(self):
        return self.generate_url(page=self.page, per_page=self.per_page)

    @property
    def prev_page_url(self):
        if self.page > 1:
            return self.generate_url(page=self.page - 1, per_page=self.per_page)

    @property
    def next_page_url(self):
        if self.page < self.pages:
            return self.generate_url(page=self.page + 1, per_page=self.per_page)

    @property
    def limit(self):
        return self.per_page

    @property
    def offset(self):
        return (self.page - 1) * self.per_page


class PaginationError(Exception):
    def __init__(self, page, status_code=400):
        self.message = []
        if page.per_page > 100:
            self.message.append('Max per_page is 100.')
        else:
            if page.page > 1:
                self.message.append('Page %s out of range, collection has %s pages.'
                                    % (page.page, page.pages))
            if page.page < 1:
                self.message.append('Page %s out of range, pages start at 1.'
                                    % page.page)

        self.status_code = status_code
        self.response = dict(errors=dict(status_code=status_code, message=self.message))
        super(PaginationError, self).__init__(self.message)
