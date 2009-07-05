import time, yaml, urllib, datetime, logging

from google.appengine.ext import db
from google.appengine.api import datastore_types

class Category(db.Model):

    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    def id(self):
        return self.name

class Builder(db.Model):

    max_build_age = datetime.timedelta(0, 3600, 0)

    category = db.ReferenceProperty(Category)
    name = db.StringProperty(required=True)
    latest_build = db.IntegerProperty()
    latest_build_result = db.StringProperty()
    current_build = db.IntegerProperty()
    current_step = db.StringProperty()

    def id(self):
        return self.name

    def is_building(self):
        if not self.current_build:
            logging.info("No current build from %s, returning False",
                         self.name)
            return False

        build = self.get_build(self.current_build)
        if not build:
            logging.info("Couldn't find current build from %s.", self.name)
            return False

        age = datetime.datetime.now() - build.started
        logging.info("Found a build from %s started at %s (%s ago)",
                     self.name, build.started, age)
        if age > self.max_build_age:
            logging.info("Current build is too old:  %s - %s = %s" %
                         (str(datetime.datetime()), str(build.started),
                          str(datetime.datetime() - build.started)))
            return False

        logging.info("Currently building on %s.", self.name)
        return True

    def get_build(self, n):
        query = BuildStatus.all()
        query.filter('builder = ', self)
        query.filter('buildNumber =', n)
        return query.get()

class BuildStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    result = db.StringProperty()
    reason = db.StringProperty()
    revision = db.StringProperty(required=True)
    patch = db.TextProperty()
    buildNumber = db.IntegerProperty(required=True)
    started = db.DateTimeProperty(auto_now=True)
    finished = db.DateTimeProperty()

class StepStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    name = db.StringProperty(required=True)
    buildNumber = db.IntegerProperty(required=True)
    status = db.StringProperty(required=True)
    logs = db.StringListProperty()
    created = db.DateTimeProperty(auto_now_add=True)

    def log_grok(self):
        return ((urllib.unquote_plus(x[x.rfind('/')+1:]), x) for x in self.logs)
