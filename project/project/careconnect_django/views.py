from io import BytesIO

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from app import app as flask_app


@csrf_exempt
def flask_application(request):
    return flask_wsgi_response(request)


def flask_wsgi_response(request):
    environ = request.META.copy()
    environ["wsgi.input"] = BytesIO(request.body)
    environ["wsgi.errors"] = _NoOpErrorStream()
    environ["QUERY_STRING"] = request.META.get("QUERY_STRING", "")
    environ["PATH_INFO"] = request.path_info
    environ["SCRIPT_NAME"] = ""
    environ["REQUEST_METHOD"] = request.method
    environ["SERVER_NAME"] = request.get_host().split(":")[0]
    environ["SERVER_PORT"] = request.get_port()
    environ["wsgi.url_scheme"] = request.scheme
    environ["wsgi.multithread"] = True
    environ["wsgi.multiprocess"] = False
    environ["wsgi.run_once"] = False
    environ["CONTENT_TYPE"] = request.META.get("CONTENT_TYPE", "")
    environ["CONTENT_LENGTH"] = str(len(request.body))

    status_headers = {}

    def start_response(status, headers, exc_info=None):
        status_headers["status"] = status
        status_headers["headers"] = headers

    body = b"".join(flask_app(environ, start_response))
    status = int(status_headers["status"].split(" ", 1)[0])
    response = HttpResponse(body, status=status)
    for name, value in status_headers["headers"]:
        response[name] = value
    return response


class _NoOpErrorStream:
    def write(self, message):
        pass

    def flush(self):
        pass
