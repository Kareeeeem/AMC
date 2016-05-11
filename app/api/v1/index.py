from app.lib import make_url

from . import v1


@v1.route('', methods=['GET'])
def index():
    routes = {name: make_url(route) for name, route in
              [('login', 'v1.login'),
               ('register', 'v1.post_users'),
               ('profile', 'v1.get_profile')]}
    return routes
