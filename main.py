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
import logging
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
from models import *

class Upvote(webapp.RequestHandler):
    def get(self):
        
        user = self.request.get("user")
        post = self.request.get("key")
        user = db.GqlQuery("SELECT * FROM User WHERE user = :1", user).fetch(1)
        print user
        #stories = stories.append(post)
        #print stories
        #stories.put()

class Judge(webapp.RequestHandler):
    def get(self):
        pass
        
class MainPage(webapp.RequestHandler):
    def get(self):
        linktext = 'Log Out'
        posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 20")

        template_values = {'user': users.get_current_user(),
                          'linktext': 'Log Out',
                          'posts': posts}

        self.response.out.write(template.render('static/index.html', template_values))                                                                   

        
class Scrape(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:  
            base = 'http://api.thriftdb.com/api.hnsearch.com/items/_search?'
            url = base + '%s%s%s' % ('&filter[fields][create_ts]=[NOW-24HOURS%20TO%20NOW]',
                                         '&limit=100',
                                         '&filter[fields][type]=submission')
            logging.info('URL - %s' %url)
            response = urllib2.urlopen(url)
            content = json.loads(response.read())
            for item in content['results']:
                if not db.GqlQuery("SELECT * FROM Node WHERE hn_id = %s" % item['item']['id']).get(): 
                    i = item['item']
                    scraped_content = Node(hn_id = i['id'],
                                           type = i['type'],
                                           url = i['url'] if i['url'] else "http://news.ycombinator.com/item?id=%s" % id, 
                                           domain = i['domain'] if i['domain'] else "http://news.ycombinator.com/",
                                           title = i['title'],
                                           commentcount = i['num_comments'],
                                           username = i['username'],
                                           points = i['points'],
                                           #timestamp = i['create_ts'],
                                           )
                    scraped_content.put()
                
                            
        else: 
            self.redirect(users.create_login_url(self.request.uri))
        
        self.redirect('/')
