import logging

import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.web
import tornado.httpclient

import config

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(message)s')

localPort = config.current['localPort']
remoteHost = config.current['remoteHost']

logging.info('localPort: %d' % localPort)
logging.info('remoteHost: %s' % remoteHost)

live_contexts = dict()

def calc_hash(request):
    "Calculate hash value by request object. To be used as key in dictionary"
    return request.uri


class Context:
    """Request context, contains request and handler objects.

    One context object accumulates multiple handler object of the same request
    before response of the first request comes back from remote host, then write
    all handlers when the response comes back."""
    def __init__(self, handler):
        self.logger = logging.getLogger('f2s2.Context')

        self.request = handler.request
        self.handlers = [handler]
        self.hashkey = calc_hash(handler.request)

        self.logger.info('new context for %s %s' % (self.request.method, self.request.uri))

    def append(self, handler):
        self.handlers.append(handler)

        self.logger.info('append handler for %s %s' % (self.request.method, self.request.uri))

    def render_response(self, response):
        for handler in self.handlers:
            handler.set_status(response.code)
            for (k, v) in response.headers.items():
                handler.set_header(k, v)
            if response.body:
                handler.write(response.body)
            handler.finish()

        if self.hashkey in live_contexts:
            del live_contexts[self.hashkey]

    def server_error(self, e):
        for handler in self.handlers:
            handler.set_status(500)
            handler.write('Internal server error:\n' + str(e))
            handler.finish()

        if self.hashkey in live_contexts:
            del contexts[self.hashkey]


class FunnelHandler(tornado.web.RequestHandler):
    "Handling funneled requests"
    @tornado.web.asynchronous
    def get(self):
        def make_request(context):
            def handle_response(response):
                if response.error and not isinstance(response.error, tornado.httpclient.HTTPError):
                    context.server_error(response.error)
                else:
                    context.render_response(response)

            req = tornado.httpclient.HTTPRequest(
                    url = remoteHost + context.request.uri,
                    method = context.request.method,
                    body = context.request.body,
                    headers = context.request.headers,
                    follow_redirects = False,
                    allow_nonstandard_methods = True
                    )

            client = tornado.httpclient.AsyncHTTPClient()
            try:
                client.fetch(req, handle_response)
            except tornado.httpclient.HTTPError as e:
                if hasattr(e, 'response') and e.response:
                    handle_response(e.response)
                else:
                    context.server_error(e)

        hashkey = calc_hash(self.request)
        if hashkey in live_contexts:
            live_contexts[hashkey].append(self)
        else:
            context = Context(self)
            live_contexts[hashkey] = context
            make_request(context)


if __name__ == '__main__':
    app = tornado.web.Application([
        (r'.*', FunnelHandler),
        ])
    app.listen(localPort)

    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.start()

