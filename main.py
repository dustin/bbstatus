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
            getattr(self, mname)()
            self.response.set_status(204)
        else:
            self.response.set_status(406)
            self.response.out.write("Unhandled event.\n")

    def handle_builderAdded(self):
        cat_name = self.request.POST['category']
        cat = models.Category.get_or_insert(cat_name,
                                            name=cat_name)

        builder_name = self.request.POST['builder']
        models.Builder.get_or_insert(builder_name,
                                     name=builder_name,
                                     category=cat)

    def handle_builderRemoved(self):
        k = db.Key.from_path('Builder', self.request.POST['builder'])
        db.delete(k)

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
