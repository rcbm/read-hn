"""
If we wanted to do pages as well as just the link title, we could:

from BeautifulSoup import BeautifulSoup
from urllib import urlopen
soup = BeautifulSoup(urlopen("<<<url>>>").read())
contents = ''.join(soup.findAll(text=True))

to extract the text, then throw everything in the classifier

"""
"""
User clicks an arrow, key + direction are ajax'd to /vote. vote trains the classifier, then 
calls Reload which sends info back out through ajax to the page
"""
"""
user clicks down on a link, it fades out, we request a bunch of new new articles from the db.
for each article we classify it, and if it fills the threshold we push it to the user.

"""

import os
import datetime
import simplejson as json
import urllib2
from logging import info as log
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue

from classifier import *
from models import *

class Vote(webapp.RequestHandler):
    def __init__(self):

        # Load user
        user = users.get_current_user()
        self.user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % user.user_id()).get()

        # Instantiate the classifier
        self.cl = naivebayes(self.user, getwords)

        self.cl.setthreshold('bad', 2.0)
        
    def reload(self, user):
        '''
        pull out a bunch of entries. classify each one. take the strongest
        one corresponding with 'up' and display it.

        make sure not to pull any that have already been voted on, OR
        are already being displayed.
        '''

        count = 0
        down = True
        while down and count < 100:
            #print count
            count += 10
            posts = db.GqlQuery("SELECT * FROM Node ORDER BY created, points ASC").fetch(100)
            for p in posts:
                cat = self.cl.classify(p.title, default='unknown')
                log(cat)
                if cat == 'up':
                    log('****FOUND ONE**** %s' %p.title)
                    return p
        
        log('couldnt find anything')
        return db.GqlQuery("SELECT * FROM Node ORDER BY created, points ASC").get()
        #return story
    
    def get(self):
        user = self.user
        
        # Load story
        key = self.request.get("key")
        story = db.get(key)

        # Which direction was clicked?
        dir = str(self.request.get("dir"))

        # Save the story's key
        user_stories = user.stories.setdefault(dir, [])
        user.stories[dir].append(story.key())
        user.put()
        
        log('TRAINING:  "%s" | %s' %(story.title, dir))
        self.cl.train(story.title, dir)

        newstory = self.reload(user).to_dict()
        log(newstory)
        self.response.out.write(json.dumps(newstory))


        
        
        #self.response.out.write(
        # Set the Threshold

        #print cl.classify('rabbit', default='unknown')
        #print cl.classify('money', default='unknown')
        #print cl.classify('money', default='unknown')
        #print cl.classify('money', default='unknown')
        #self.redirect('/')
        
        
class MainPage(webapp.RequestHandler):
    def get(self):
        temp_user = users.get_current_user()
        if temp_user:
            user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % temp_user.user_id()).get()
            if not user:
                new_user = User(user = temp_user,
                                user_id = temp_user.user_id(),
                                email = temp_user.email())
                new_user.put()
                user = new_user                

            posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 10")
            template_values = {'user': users.get_current_user(),
                               'logout_url': users.create_logout_url("/"),
                               'posts': posts}
            
            self.response.out.write(template.render('static/index.html', template_values))                                                                   
        else:
            self.redirect(users.create_login_url(self.request.uri))

            
class ScrapeHandler(webapp.RequestHandler):
    def get(self):
        if not db.GqlQuery("SELECT * FROM StopWord").get():
            import stopwords as s
            db.put([StopWord(word = w) for w in s.words()])
            
        for x in range(10):
            taskqueue.add(url="/scrape_bot", params={'start': (x*100)})

            
class ScrapeBot(webapp.RequestHandler):
    def post(self):
            base = 'http://api.thriftdb.com/api.hnsearch.com/items/_search?'
            url = base + '%s%s%s' % ('&filter[fields][create_ts]=[NOW-48HOURS%20TO%20NOW]',
                                     '&limit=100', '&filter[fields][type]=submission')
            req = url + '&start=%s' % self.request.get("start")
            log('URL - %s' %req)
            hn_url = "http://news.ycombinator.com/"
            response = urllib2.urlopen(req)
            content = json.loads(response.read())
            for item in content['results']:
                if not db.GqlQuery("SELECT * FROM Node WHERE hn_id = %s" % item['item']['id']).get(): 
                    i = item['item']
                    scraped_content = Node(hn_id = i['id'], type = i['type'],
                                           url = i['url'] if i['url'] else hn_url + "item?id=%s" % id, 
                                           domain = i['domain'] if i['domain'] else hn_url,
                                           title = i['title'], commentcount = i['num_comments'],
                                           username = i['username'], points = i['points'])
                    scraped_content.put()
