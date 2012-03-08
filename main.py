'''
THINGS TO-DO:
------------
-Build scraper
-Build system to pull things out of db and show them for user
-Build system to rank an article and save rank info
-Build classifier

BUGS:
------------


###########################################################################################

DONE
-------------
-Build model

'''

import os
import logging
import datetime
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
from models import *


class MainPage(webapp.RequestHandler):
    def get(self):
        if users.get_current_user():
            self.response.out.write('<html><head></head><body>penus</body></html>')
        else:
            self.redirect(users.create_login_url(self.request.uri))









        
        print 'PENUS'
        #now = str(datetime.now()).split('.')[0]
        #events = db.GqlQuery("SELECT * FROM Event WHERE datetime > DATETIME('%s') AND active=True LIMIT 100" % now)
        #self.response.out.write(template.render('static/index.html', { 'linktext': self.linktext,
        #                                                               'events': events }))
        

