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
            linktext = 'Log Out'
            
            #now = str(datetime.now()).split('.')[0]
            #stories = db.GqlQuery("SELECT * FROM Node WHERE datetime > DATETIME('%s') AND active=True LIMIT 100" % now)
            self.response.out.write(template.render('static/index.html', { 'user': users.get_current_user(),
                                                                           'linktext': linktext}))

        else:
            self.redirect(users.create_login_url(self.request.uri))
            
