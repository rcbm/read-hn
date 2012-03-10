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
import json
import urllib2
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
from models import *

class MainPage(webapp.RequestHandler):
    def get(self):
        linktext = 'Log Out'
        self.response.out.write(template.render('static/index.html', { 'user': users.get_current_user(),
                                                                       'linktext': linktext}))
# needs urlfetch
class Scrape(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:    
            response = urllib2.urlopen('http://api.ihackernews.com/new')
            content = json.loads(response.read())
            for i in content['items']:
                commentCount = i['commentCount']
                id = i['id']
                url = i['url']
                title = i['title']
                postedBy = i['postedBy']
                points = i['points']
                postedAgo = i['postedAgo']
                scraped_content = Node( hn_id = id,
                                        url = url,
                                        title = title,
                                        commentcount = commentCount,
                                        username = postedBy,
                                        points = points)
                if not "SELECT * FROM Node WHERE hn_id = %s" % id : 
                    scraped_content.put()
                else:
                    pass
                                                    
                            
        else: 
            self.redirect(users.create_login_url(self.request.uri))        
        
