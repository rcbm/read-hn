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

        print 'PENUS'
        #now = str(datetime.now()).split('.')[0]
        #events = db.GqlQuery("SELECT * FROM Event WHERE datetime > DATETIME('%s') AND active=True LIMIT 100" % now)
        #self.response.out.write(template.render('static/index.html', { 'linktext': self.linktext,
        #                                                               'events': events }))
        
# needs urlfetch
class Scrape(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:    
            response = urllib2.urlopen('http://api.ihackernews.com/page')
            content = json.loads(response.read())
            for i in content['items']:
                commentCount = i['commentCount']
                id = i['id']
                url = i['url']
                title = i['title']
                postedBy = i['postedBy']
                points = i['points']
                postedAgo = i['postedAgo']
                scraped_content = Node( id = id,
                                        url = url,
                                        title = title,
                                        commentcount = commentCount,
                                        username = postedBy,
                                        points = points)
                scraped_content.put()                                    
                            
        else: 
            self.redirect(users.create_login_url(self.request.uri))        
        
        
        
        