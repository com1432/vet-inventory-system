from django.db import connection

class ConnectionCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        connection.close_if_unusable_or_obsolete()
        return response