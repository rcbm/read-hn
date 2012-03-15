import pickle
from google.appengine.ext import db
from google.appengine.api import users

class DictProperty(db.Property):
  data_type = dict

  def get_value_for_datastore(self, model_instance):
    value = super(DictProperty, self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return dict()
    return pickle.loads(value)

  def default_value(self):
    if self.default is None:
      return dict()
    else:
      return super(DictProperty, self).default_value().copy()

  def validate(self, value):
    if not isinstance(value, dict):
      raise db.BadValueError('Property %s needs to be convertible '
                             'to a dict instance (%s) of class dict' % (self.name, value))
    return super(DictProperty, self).validate(value)

  def empty(self, value):
    return value is None
  
class Node(db.Model):
    hn_id = db.IntegerProperty(required=True)
    type = db.StringProperty(required=True)
    url = db.StringProperty(required=False)
    domain = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    commentcount = db.IntegerProperty()
    username = db.StringProperty(required=True)
    points = db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
class StopWord(db.Model):
    word = db.StringProperty(required=True)

class User(db.Model):
    user = db.UserProperty(required=True)
    user_id = db.StringProperty(required=True)
    updated = db.DateTimeProperty(auto_now=True)
    email = db.EmailProperty()
    stories = DictProperty()
    catcount = DictProperty()
    fdict = DictProperty()
