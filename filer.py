#!/usr/bin/env python

import os
from os.path import join
from tornado import httpserver, ioloop, web
from tornado.options import define, options
from credentials import username, password
from github3 import login


define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)


class Application(web.Application):
    def __init__(self):
        handlers = [
            (r"/uploads/(.*)/(.*)/$", UploadHandler),
        ]
        web.Application.__init__(self, handlers, debug=options.debug)


# touch 1.qzv 2.qzv 3.qzv
# curl -POST -F "files[]=@1.qzv" -F "files[]=@2.qzv" -F "files[]=@3.qzv"
# mchelper.ucsd.edu:8888/uploads/empress/master/
class UploadHandler(web.RequestHandler):
    def post(self, repo, branch):
        # we are expecting 3 artifacts but we want a bit more space
        if int(self.request.headers['Content-Length']) >= (2023660 * 4):
            raise web.HTTPError(413, "File too large!")

        path = join('/var/www/html/downloads/', repo, branch)
        os.makedirs(path, exist_ok=True)

        responses = []
        for file in self.request.files['files[]']:
            if not file['filename'].endswith('.qzv'):
                raise web.HTTPError(500, "Only visualizations are allowed, "
                                    "invalid extension")

        for file in self.request.files['files[]']:
            with open(join(path, file['filename']), 'wb') as f:
                f.write(file['body'])

            url = (("https://view.qiime2.org/visualization/?type=html&src="
                    "https%%3A%%2F%%2Fmchelper.ucsd.edu%%2Fdownloads%%2F%s"
                    "%%2F%s%%2F%s") %
                   (repo, branch, file['filename']))

            responses.append(url)

        # only write a comment if we are pushing PR artifacts
        if branch != 'master':
            post_comment_with_link(repo, branch, responses)

        self.finish('\n'.join(responses))


def post_comment_with_link(repo, branch, urls):
    gh = login(username, password)
    pr = gh.pull_request('biocore', repo, branch)

    # if no posts by emperor-helper then post a comment
    post_comment = all([c.user.login != username for c in pr.issue_comments()])

    if post_comment:
        # create the necessary markdown
        artifacts = []
        for url in urls:
            # get the name of the file
            name = url.split('%2F')[-1]
            artifacts.append('[%s](%s)' % (name, url))
        artifacts = ', '.join(sorted(artifacts))

        text = 'The following artifacts were built for this PR: %s' % artifacts

        _ = pr.create_comment(text)


def main():
    http_server = httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    print("Starting server: ", options.port)
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
