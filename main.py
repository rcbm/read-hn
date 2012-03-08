'''
THINGS TO-DO:

BUGS:
------------


Not Urgent
_____________


Harder:
-------------


###########################################################################################

DONE
-------------

'''

import os
import logging
import datetime
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
#from models import *


class MainPage(webapp.RequestHandler):
    def get(self):
        print 'PENUS'
        #now = str(datetime.now()).split('.')[0]
        #events = db.GqlQuery("SELECT * FROM Event WHERE datetime > DATETIME('%s') AND active=True LIMIT 100" % now)
        #self.response.out.write(template.render('static/index.html', { 'linktext': self.linktext,
        #                                                               'events': events }))
        

