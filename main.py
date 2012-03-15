"""
If we wanted to do pages as well as just the link title, we could:

from BeautifulSoup import BeautifulSoup
from urllib import urlopen
soup = BeautifulSoup(urlopen("<<<url>>>").read())
contents = ''.join(soup.findAll(text=True))

to extract the text, then throw everything in the classifier

"""
"""
user clicks down on a link, it fades out, we request a bunch of new new articles from the db.
for each article we classify it, and if it fills the threshold we push it to the user.


"""

import os
import datetime
import json
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
    def post(self):
        # Load user
        user = users.get_current_user()
        user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % user.user_id()).get()

        cl = naivebayes(user, getwords)
        
        # Load story
        key = self.request.get("key")
        story = db.get(key)

        # Which direction was clicked?
        dir = str(self.request.get("dir"))

        # Store the story key in the right category
        user_stories = user.stories.setdefault(dir, [])
        user.stories[dir].append(story.key())
        user.put()
        
        log('Training "%s" | %s' %(story.title, dir))
        cl.train(story.title, dir)

        # Threshold
        #cl.setthreshold('bad', 2.0)

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
        #if not db.GqlQuery("SELECT * FROM StopWord").get():
        #    self.loadStopWords()

        for x in range(10):
            taskqueue.add(url="/scrape_bot", params={'start': (x*100)})

class ScrapeBot(webapp.RequestHandler):
    def post(self):
            base = 'http://api.thriftdb.com/api.hnsearch.com/items/_search?'
            url = base + '%s%s%s' % ('&filter[fields][create_ts]=[NOW-24HOURS%20TO%20NOW]',
                                     '&limit=100',
                                     '&filter[fields][type]=submission')
            req = url + '&start=%s' % self.request.get("start")
            log('URL - %s' %req)
            response = urllib2.urlopen(req)
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
                                           points = i['points'])
                    scraped_content.put()

class LoadStopWords(webapp.RequestHandler):
    def get(self):
        dict = ['a', 'about', 'above', 'across', 'after', 'afterwards', 
                'again', 'against', 'all', 'almost', 'alone', 'along', 
                'already', 'also', 'although', 'always', 'am', 'among', 
                'amongst', 'amoungst', 'amount', 'an', 'and', 'another', 
                'any', 'anyhow', 'anyone', 'anything', 'anyway', 'anywhere', 
                'are', 'around', 'as', 'at', 'back', 'be', 
                'became', 'because', 'become', 'becomes', 'becoming', 'been', 
                'before', 'beforehand', 'behind', 'being', 'below', 'beside', 
                'besides', 'between', 'beyond', 'bill', 'both', 'bottom', 
                'but', 'by', 'call', 'can', 'cannot', 'cant', 'dont',
                'co', 'computer', 'con', 'could', 'couldnt', 'cry', 
                'de', 'describe', 'detail', 'do', 'done', 'down', 
                'due', 'during', 'each', 'eg', 'eight', 'either', 
                'eleven', 'else', 'elsewhere', 'empty', 'enough', 'etc', 'even', 'ever', 'every', 
                'everyone', 'everything', 'everywhere', 'except', 'few', 'fifteen', 
                'fifty', 'fill', 'find', 'fire', 'first', 'five', 
                'for', 'former', 'formerly', 'forty', 'found', 'four', 
                'from', 'front', 'full', 'further', 'get', 'give', 
                'go', 'had', 'has', 'hasnt', 'have', 'he', 
                'hence', 'her', 'here', 'hereafter', 'hereby', 'herein', 
                'hereupon', 'hers', 'herself', 'him', 'himself', 'his', 
                'how', 'however', 'hundred', 'i', 'ie', 'if', 
                'in', 'inc', 'indeed', 'interest', 'into', 'is', 
                'it', 'its', 'itself', 'keep', 'last', 'latter', 
                'latterly', 'least', 'less', 'ltd', 'made', 'many', 
                'may', 'me', 'meanwhile', 'might', 'mill', 'mine', 
                'more', 'moreover', 'most', 'mostly', 'move', 'much', 
                'must', 'my', 'myself', 'name', 'namely', 'neither', 
                'never', 'nevertheless', 'next', 'nine', 'no', 'nobody', 
                'none', 'noone', 'nor', 'not', 'nothing', 'now', 
                'nowhere', 'of', 'off', 'often', 'on', 'once', 
                'one', 'only', 'onto', 'or', 'other', 'others', 
                'otherwise', 'our', 'ours', 'ourselves', 'out', 'over', 
                'own', 'part', 'per', 'perhaps', 'please', 'put', 
                'rather', 're', 'same', 'see', 'seem', 'seemed', 
                'seeming', 'seems', 'serious', 'several', 'she', 'should', 
                'show', 'side', 'since', 'sincere', 'six', 'sixty', 
                'so', 'some', 'somehow', 'someone', 'something', 'sometime', 
                'sometimes', 'somewhere', 'still', 'such', 'system', 'take', 
                'ten', 'than', 'that', 'the', 'their', 'them', 
                'themselves', 'then', 'thence', 'there', 'thereafter', 'thereby', 
                'therefore', 'therein', 'thereupon', 'these', 'they', 'thick', 
                'thin', 'third', 'this', 'those', 'though', 'three', 
                'through', 'throughout', 'thru', 'thus', 'to', 'together', 
                'too', 'top', 'toward', 'towards', 'twelve', 'twenty', 
                'two', 'un', 'under', 'until', 'up', 'upon', 
                'us', 'very', 'via', 'was', 'we', 'well', 
                'were', 'what', 'whatever', 'when', 'whence', 'whenever', 
                'where', 'whereafter', 'whereas', 'whereby', 'wherein', 'whereupon', 
                'wherever', 'whether', 'which', 'while', 'whither', 'who', 
                'whoever', 'whole', 'whom', 'whose', 'why', 'will', 
                'with', 'within', 'without', 'would', 'yet', 'you', 'your', 'yours', 
                'yourself', 'yourselves','1','2','3','4','5','6','7','8','9','0','-',
                '?',']',')','}','[','(','{',';','|',':']

        db.put([StopWord(word = x) for x in dict])
