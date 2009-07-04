import datetime

import wsgiref.handlers

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template

import models

class CategoryHandler(webapp.RequestHandler):

    def get(self):
        cat = db.get(db.Key.from_path('Category', self.request.path[1:]))
        builders = models.Builder.all().filter('category = ', cat).fetch(1000)
        self.response.out.write(template.render(
                'templates/cat.html', {'cat': cat, 'builders': builders}))


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
        builder = self._get_builder()
        p = self.request.POST

        bs = models.BuildStatus(builder=builder, reason=p['reason'],
                                sourceStamp=p['sourceStamp'],
                                buildNumber=int(p['buildNumber']))
        db.put(bs)

    def handle_buildFinished(self):
        builder = self._get_builder()
        p = self.request.POST

        query = models.BuildStatus.all()
        query.filter('builder = ', builder)
        query.filter('buildNumber =', int(p['buildNumber']))

        build = query.get()
        if build:
            build.finished = datetime.datetime.now()
            build.result = p['result']
            build.put()

            builder.latest_build = int(p['buildNumber'])
            builder.latest_build_result = p['result']
            builder.put()
        else:
            self.response.set_status(404)

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
        cats = sorted(c.name() for c in models.Category.all(keys_only=True).fetch(100))
        self.response.out.write(template.render(
                'templates/index.html', {'cats': cats}))

def main():
    application = webapp.WSGIApplication([
            ('/', MainHandler),
            ('/webhook', HookHandler),
            ('/.*', CategoryHandler)], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
