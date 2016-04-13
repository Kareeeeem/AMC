from marshmallow import (
    Schema as _Schema,
    SchemaOpts as _SchemaOpts,
    fields,
    post_dump,
)


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta):
        _SchemaOpts.__init__(self, meta)
        self.strict = True


class Schema(_Schema):
    OPTIONS_CLASS = SchemaOpts

    def __init__(self, page=None, expand=None, *args, **kwargs):
        super(Schema, self).__init__(*args, **kwargs)
        self.expand = expand or []
        self.page = page

    class PaginationSchema(_Schema):
        page = fields.Integer()
        pages = fields.Integer()
        per_page = fields.Integer()

        total = fields.Integer(attribute='total_count')
        next = fields.Url(attribute='next_page_url')
        prev = fields.Url(attribute='prev_page_url')
        first = fields.Url(attribute='first_page_url')
        last = fields.Url(attribute='last_page_url')
        current = fields.Url(attribute='current_page_url')

    @post_dump(pass_many=True)
    def wrap_in_pagination(self, data, many):
        if many and self.page:
            page = self.PaginationSchema().dump(self.page).data
            page.update(items=data)
            return page
