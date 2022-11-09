import json
import socket
import ftplib
import traceback
import http.cookiejar
import urllib.parse
import urllib.error as error
import urllib.request as urllib2

errors = (error.URLError, error.HTTPError, error.ContentTooShortError) + \
         (socket.gaierror, ) + \
         ftplib.all_errors


class IgnoreHttpErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, hdrs):
        # raise HTTPError(req.full_url, code, msg, hdrs, fp)
        return fp


class HttpFactory:
    def __init__(self, url, params=None, headers=None, timeout=None, **kwargs):
        """ http request have a faster response time than `requests` package """
        self.url = url
        self.data = None
        self.params = params or {}
        self.headers = headers or {}
        self.timeout = timeout or 5

        self.ignore_error = kwargs.pop("ignore_error", False)
        self.kwargs = kwargs

        self._response = None
        self.add_headers(
            key="User-Agent",
            value="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        )

    def get(self):
        self.urlopen(method="GET")
        return self._parse_response()

    def post(self, data=None):
        self.data = data
        self.urlopen(method="POST")

        return self._parse_response()

    def _parse_response(self):
        headers = self._response.headers
        content_type = headers.get("Content-Type", "")
        raw_content = self._response.read()

        if "application/json" in content_type:
            result = json.loads(raw_content)
        else:
            charset = headers._charset
            if charset is None:
                charset = "utf-8"

            result = raw_content.decode(charset)

        return result

    def __del__(self):
        if hasattr(self._response, "close"):
            self._response.close()

    def add_headers(self, key=None, value=None, headers=None, **kwargs):
        self.headers.update(headers or {}, **kwargs)

        if key:
            self.headers[key] = value

    def _get_handlers(self):
        handlers = []

        cookie_jar = http.cookiejar.CookieJar()
        cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
        handlers.append(cookie_handler)

        if self.ignore_error:
            handlers.append(IgnoreHttpErrorHandler)

        return handlers

    def _set_opener(self):
        opener = urllib2.build_opener(*self._get_handlers())
        urllib2.install_opener(opener)

        return opener

    def urlopen(self, method="GET"):
        assert method in ["GET", "POST"], "Method:%s not allowed!" % method

        self._set_opener()

        url = self.url
        data = self.data
        params = urllib.parse.urlencode(self.params)

        if params:
            url = "%s?%s" % (self.url, params)

        if data is not None:
            content_type = self.headers.get("Content-Type", "")

            if "application/json" in content_type:
                data = json.dumps(data).encode("utf-8")  # Json
            elif "multipart" in content_type:
                # file upload
                data = bytes(data) if not isinstance(data, bytes) else data
            else:
                data = urllib.parse.urlencode(data).encode("utf-8")

        request = urllib2.Request(url, data=data, headers=self.headers, method=method)
        try:
            self._response = urllib2.urlopen(request)
        except errors:
            traceback.format_exc()

