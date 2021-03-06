import datetime
import urllib

import wsgiref.handlers

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template

import models

class CategoryHandler(webapp.RequestHandler):

    def get(self, cat_name):
        cat = db.get(db.Key.from_path('Category', urllib.unquote_plus(cat_name)))
        if not cat:
            self.response.set_status(404)
            self.response.out.write("No such category: %s" % cat_name)

        self.response.out.write(template.render(
                'templates/cat.html', {'cat': cat}))

class BuildHandler(webapp.RequestHandler):

    def get(self, category_name, builder_name, buildnum):
        k = db.Key.from_path('Builder', urllib.unquote_plus(builder_name))
        builder = models.Builder.get(k)

        status = builder.get_build(int(buildnum))

        if not status:
            self.response.set_status(404)
            self.response.out.write("Build not found.")
            return

        self.response.out.write(template.render(
                'templates/build.html', {'build': status}))

class HookHandler(webapp.RequestHandler):

    def post(self):
        mname = 'handle_' + self.request.POST.get('event', 'unknown')
        if hasattr(self, mname):
            self.response.set_status(204)
            getattr(self, mname)()
        else:
            self.response.set_status(406)
            self.response.out.write("Unhandled event.\n")

    def handle_builderAdded(self):
        self._get_builder()

    def handle_builderRemoved(self):
        k = db.Key.from_path('Builder', self.request.POST['builder'])
        db.delete(k)

    def handle_buildStarted(self):
        p = self.request.POST

        builder = self._get_builder()
        builder.current_build = int(p['buildNumber'])
        builder.put()

        bs = models.BuildStatus(builder=builder, reason=p['reason'],
                                revision=p['revision'],
                                patch=p.get("patch", None),
                                buildNumber=int(p['buildNumber']))
        db.put(bs)

    def handle_buildFinished(self):
        builder = self._get_builder()
        p = self.request.POST

        build = builder.get_build(int(p['buildNumber']))

        if build:
            build.finished = datetime.datetime.now()
            build.result = p['result']
            build.put()

            builder.latest_build = int(p['buildNumber'])
            builder.latest_build_result = p['result']
            builder.current_build = None
            builder.current_step = None
            builder.put()
        else:
            self.response.set_status(404)

    def handle_stepStarted(self):
        b = self._get_builder()
        b.current_step = self.request.get("step")
        b.put()

    def handle_stepFinished(self):
        p = self.request.POST
        ss = models.StepStatus(builder=self._get_builder(),
                               name=p['step'],
                               buildNumber=int(p['buildNumber']),
                               status=p['resultStatus'],
                               logs=self.request.get_all('logFile'))
        ss.put()

    def _get_builder(self):
        cat_name = self.request.POST['category']
        cat = models.Category.get_or_insert(cat_name,
                                            name=cat_name)

        builder_name = self.request.POST['builder']
        return models.Builder.get_or_insert(builder_name,
                                            name=builder_name,
                                            category=cat)

class MainHandler(webapp.RequestHandler):

    def get(self):
        cats = models.Category.all().order('name').fetch(100)
        self.response.out.write(template.render(
                'templates/index.html', {'cats': cats}))

def main():
    application = webapp.WSGIApplication([
            ('/', MainHandler),
            ('/webhook', HookHandler),
            ('/(.*)/(.*)/build/(.*)', BuildHandler),
            ('/(.*)', CategoryHandler)], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
