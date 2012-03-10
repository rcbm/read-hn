from google.appengine.ext import db
from google.appengine.api import users

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
    
class User(db.Model):
    user = db.UserProperty(required=True)
    user_id = db.StringProperty(required=True)
    email = db.EmailProperty()
    stories = db.ListProperty(db.Key)
    priors = db.StringProperty() 
