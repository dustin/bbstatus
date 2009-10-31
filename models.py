import time, yaml, urllib, datetime, logging

from google.appengine.ext import db
from google.appengine.api import datastore_types
from google.appengine.api import memcache

CACHE_VERSION=2

def cached(key_func):
    def f(orig):
        def every(self):
            k = key_func(self)
            rv = memcache.get(k)
            if rv is None:
                rv = orig(self)
                logging.info("Setting %s to %s in cache", k, rv)
                memcache.set(k, rv)
            else:
                logging.info("Got %s from cache", k)
            return rv
        return every
    return f

class Category(db.Model):

    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    def id(self):
        return self.name

    def _building_cache_key(self):
        return "cat:building:%s:%s" % (CACHE_VERSION, urllib.quote(self.name))

    def _builder_cache_key(self):
        return "cat:builders:%s:%s" % (CACHE_VERSION, urllib.quote(self.name))

    @cached(_builder_cache_key)
    def builders(self):
        logging.info("Finding all builders for %s", self.name)
        everything = Builder.all().filter('category = ', self).order('name').fetch(1000)
        return [e for e in everything if e.is_valid()]

    @cached(_building_cache_key)
    def is_building(self):
        logging.info("Checking to see if %s has active builders", self.name)
        return any(b.is_building() for b in self.builders())

    def __cmp__(self, o):
        return cmp(self.name, o.name)

    def _invalidate_building_cache(self):
        memcache.delete(self._building_cache_key())

    def _invalidate_builder_cache(self):
        memcache.delete_multi([self._builder_cache_key(),
                               self._building_cache_key()])


    def put(self):
        rv = super(Category, self).put()
        self._invalidate_builder_cache()
        return rv

class Builder(db.Model):

    max_builder_age = datetime.timedelta(30, 0, 0)
    max_build_age = datetime.timedelta(0, 3600, 0)

    category = db.ReferenceProperty(Category)
    name = db.StringProperty(required=True)
    latest_build = db.IntegerProperty()
    latest_build_result = db.StringProperty()
    current_build = db.IntegerProperty()
    current_step = db.StringProperty()

    def id(self):
        return self.name

    def is_valid(self):
        build = self.get_build(self.latest_build)
        if not build:
            return False

        age = datetime.datetime.now() - build.started
        logging.info("Found a build from %s started at %s (%s ago vs. %s)",
                     self.name, build.started, age, self.max_builder_age)
        return age < self.max_builder_age

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

    def put(self):
        rv = super(Builder, self).put()
        self.category._invalidate_builder_cache()
        return rv

class BuildStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    result = db.StringProperty()
    reason = db.StringProperty()
    revision = db.StringProperty(required=True)
    patch = db.TextProperty()
    buildNumber = db.IntegerProperty(required=True)
    started = db.DateTimeProperty(auto_now=True)
    finished = db.DateTimeProperty()

    def steps(self):
        query = StepStatus.all()
        query.filter('builder = ', self.builder)
        query.filter('buildNumber =', self.buildNumber)
        query.order('created')

        return query.fetch(1000)

class StepStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    name = db.StringProperty(required=True)
    buildNumber = db.IntegerProperty(required=True)
    status = db.StringProperty(required=True)
    logs = db.StringListProperty()
    created = db.DateTimeProperty(auto_now_add=True)

    def log_grok(self):
        return ((urllib.unquote_plus(x[x.rfind('/')+1:]), x) for x in self.logs)
