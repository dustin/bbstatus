import time, yaml
from google.appengine.ext import db
from google.appengine.api import datastore_types

class Category(db.Model):

    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    def id(self):
        return self.name

class Builder(db.Model):

    category = db.ReferenceProperty(Category)
    name = db.StringProperty(required=True)

    def id(self):
        return self.name

class BuildStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    result = db.StringProperty(required=True)
    sourceStamp = db.StringProperty(required=True)
    buildNumber = db.IntegerProperty(required=True)
    started = db.DateTimeProperty(auto_now=True)
    finished = db.DateTimeProperty()

class StepStatus(db.Model):

    builder = db.ReferenceProperty(Builder)
    name = db.StringProperty(required=True)
    buildNumber = db.IntegerProperty(required=True)
    status = db.StringProperty(required=True)
    logs = db.StringListProperty()
