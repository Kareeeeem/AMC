from marshmallow import Schema as _Schema, SchemaOpts as _SchemaOpts, post_dump


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta):
        _SchemaOpts.__init__(self, meta)
        self.strict = True
        self.related = getattr(meta, 'related', None)
        self.meta = getattr(meta, 'meta', None)


class Schema(_Schema):
    OPTIONS_CLASS = SchemaOpts

    def __init__(self, page=None, expand=None, *args, **kwargs):
        super(Schema, self).__init__(*args, **kwargs)
        self.expand = expand or []
        self.page = page

    @post_dump
    def format(self, data):
        rv = dict(data=data)

        if self.opts.meta:
            meta_dict = {}
            for key in self.opts.meta:
                try:
                    meta_dict[key] = data.pop(key)
                except KeyError:
                    pass
            rv.update(meta=meta_dict)

        if self.opts.related:
            related_dict = {}
            for key in self.opts.related:
                try:
                    related_dict[key] = data.pop(key)
                except KeyError:
                    pass
            rv.update(related=related_dict)

        return rv
