from rest_framework.authentication import SessionAuthentication


class SessionAuth(SessionAuthentication):
    """Session login that answers 401 (not 403) when nobody is logged in, so the dashboard shows the login screen."""

    def authenticate_header(self, request):
        return "Session"
