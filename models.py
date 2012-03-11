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
    url = db.StringProperty(required=False)
    domain = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    text = db.TextProperty(default=None)
    username = db.StringProperty(required=True)
    points = db.IntegerProperty(required=True)
    type = db.StringProperty(required=True)
    points = db.IntegerProperty(required=True)
    timestamp = db.DateTimeProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    commentcount = db.IntegerProperty()
    parentid = db.IntegerProperty()

class StopWord(db.Model):
    word = db.StringProperty(required=True)

class Features(db.Model):
    updated = db.DateTimeProperty(auto_now=True)

    down_stories = db.ListProperty(db.Key)
    up_stories = db.ListProperty(db.Key)

    num_down = db.IntegerProperty(default=1)
    num_up = db.IntegerProperty(default=1)
    
    down_unigram_dict = DictProperty()
    down_unigram_prob = DictProperty()
    down_bigram_dict = DictProperty()
    down_bigram_prob = DictProperty()

    up_unigram_dict = DictProperty()
    up_unigram_prob = DictProperty()
    up_bigram_dict = DictProperty()
    up_bigram_prob = DictProperty()
    
class User(db.Model):
    user = db.UserProperty(required=True)
    user_id = db.StringProperty(required=True)
    email = db.EmailProperty()
    feature_profile = db.ReferenceProperty(Features)
    
