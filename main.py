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

'''
When a user X's out a story, a get request is called w/ the key to /vote -> Judge
- Judge calls the breakout method
  
'''

class Judge(webapp.RequestHandler):
    def breakout(self, key):
        story = db.get(key)
        title = story.title
        
        import re
        punct = re.compile(r'[.?!,":;]') 

        # Strip punct and break down into unigrams
        unigrams = word_list = re.split('\s+', title)
        unigrams = [punct.sub("", w) for w in unigrams]

        # Count unigrams
        uni_freq_dict = {}
        for word in unigrams:
            uni_freq_dict[word] = uni_freq_dict.get(word,0) + 1
        
        # Break down into bigrams
        bigrams = []
        for index, x in enumerate(unigrams):
            if (index + 1) < len(unigrams):
                bigrams.append((x, unigrams[index + 1]))

        # Count bigrams
        bi_freq_dict = {}
        for b in bigrams: bi_freq_dict[b] = bi_freq_dict.get(b,0) + 1

        return {'uni': uni_freq_dict,
                'bi': bi_freq_dict}

    def get(self):
        user = users.get_current_user()
        ngrams = self.breakout(self.request.get("key"))
        user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % users.get_current_user().user_id()).get()

        if not user.feature_profile:
            feature = Features(unigram_dict = ngrams['uni'],
                               bigram_dict = ngrams['bi'])
            feature.put()
            user.feature_profile = feature.key()
            user.put()
        else:
            features = user.feature_profile
            unidict = features.unigram_dict
            bidict = features.bigram_dict
            
            for key in ngrams['uni']:
                unidict[key] = unidict.get(key,0) + 1
            for key in ngrams['bi']:
                bidict[key] = bidict.get(key,0) + 1
            features.put()
        self.redirect('/')
            
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

            posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 20")
            
            template_values = {'user': users.get_current_user(),
                               'url': users.create_logout_url("/"),
                               'posts': posts}
            
            self.response.out.write(template.render('static/index.html', template_values))                                                                   
        else:
            self.redirect(users.create_login_url(self.request.uri))
            
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
