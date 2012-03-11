import os
import datetime
import json
import urllib2
import logging
from math import log, exp
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
from models import *

class Break():
    def breakout(self, story):
        import re
        import unicodedata
        title = story.title
        punct = re.compile(r'[.?!,":;]') 
        
        # Load stopwords
        stopwords = [str(x.word) for x in db.GqlQuery("SELECT * FROM StopWord").fetch(1000)]
        
        # Strip punct and break down into unigrams
        unigrams = word_list = re.split('\s+', title)
        unigrams = [punct.sub("", str(unicodedata.normalize('NFKD', w).encode('ascii','ignore'))) for w in unigrams]

        # Count unigrams
        uni_freq_dict = {}
        for word in [w.lower() for w in unigrams]:
            if word not in stopwords:
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
    
    
class Judge(webapp.RequestHandler):
    def get(self):
        temp_user = users.get_current_user()
        key = self.request.get("key")
        story = db.get(key)
        ngrams = Break().breakout(story)
        user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % temp_user.user_id()).get()
        up = True if self.request.get("dir") == 'up' else False
        features = Features() if not user.feature_profile else user.feature_profile
        numdown = features.num_down
        numup = features.num_up
        denom = numup if up else numdown

        if up:
            features.num_up += 1
            features.up_stories.append(story.key())
        else:
            features.num_down += 1
            features.down_stories.append(story.key())
        
        # Map the correct features depending on the direction
        unidict = features.up_unigram_dict if up else features.down_unigram_dict
        uniprob = features.up_unigram_prob if up else features.down_unigram_prob
        bidict = features.up_bigram_dict if up else features.down_bigram_dict
        biprob = features.up_bigram_prob if up else features.down_bigram_prob

        # Add unigram counts and recalc probabilities
        for key in ngrams['uni']:
            unidict[key] = unidict.get(key,0) + 1
            if key in uniprob:
                uniprob[key] = uniprob[key] + log(1.0/denom)
            else:
                uniprob[key] = log(1.0/denom)

        # Add bigram counts and recalc probabilities
        for key in ngrams['bi']:
            bidict[key] = bidict.get(key,0) + 1
            if key in biprob:
                biprob[key] = biprob[key] + log(1.0/denom)
            else:
                biprob[key] = log(1.0/denom)

        # Save updated Features Set to Datastore
        features.put()
        if not user.feature_profile:
            user.feature_profile = features.key()
            user.put()
        
        print ''
        print 'NUMDOWN: %s' %numdown
        print 'NUMUP: %s\n' %numup

        print 'DOWN PROBABILITIES'
        print '-------------------------\n'
        for key,value in features.down_unigram_prob.iteritems():
            print '%s: %s' %(key, value)
        print ''
        for key,value in features.down_bigram_prob.iteritems():
            print '%s: %s' %(key, value)
        print '\n'

        print 'UP PROBABILITIES'
        print '-------------------------\n'
        for key,value in features.up_unigram_prob.iteritems():
            print '%s: %s' %(key, value)
        print ''
        for key,value in features.up_bigram_prob.iteritems():
            print '%s: %s' %(key, value)
        print ''

        #self.redirect('/')
            
class MainPage(webapp.RequestHandler):
    def classify(self, features):
        posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 25")
        b = Break()
        for post in posts:
            ngrams = b.breakout(post)
            for n in ngrams['uni']:
                if n in features.up_unigram_dict:
                    self.response.out.write('UP: %s : %s<BR>' %(n, features.up_unigram_dict[n]))
                if n in features.down_unigram_dict:
                    self.response.out.write('DOWN: %s : %s<BR>' %(n, features.down_unigram_dict[n]))
                    
            
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

            if not user.feature_profile:
                posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 20")
            else:
                posts = self.classify(user.feature_profile)
                
            template_values = {'user': users.get_current_user(),
                               'logout_url': users.create_logout_url("/"),
                               'posts': posts}
            
            self.response.out.write(template.render('static/index.html', template_values))                                                                   
        else:
            self.redirect(users.create_login_url(self.request.uri))
            
class Scrape(webapp.RequestHandler):
    def get(self):
        self.loadStopWords()
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

    def loadStopWords(self):
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
