import re
import os
import datetime
import json
import urllib2
import logging
from unicodedata import normalize
from math import log, exp, fabs
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import taskqueue
from models import *

def getwords(text, stopwords):
    # Split the words by non-alpha characters
    words = [s.lower() for s in re.compile('\\W*').split(text)
             if len(s) > 2 and len(s) < 20]

    # Remove stop words
    words = [w for w in words if w not in stopwords]

    return dict([(w, 1) for w in words])

class classifier:
    def __init__(self, user, getfeatures):
        self.user = user

        # Load stopwords
        self.stopwords = [str(x.word) for x in db.GqlQuery("SELECT * FROM StopWord").fetch(1000)]

        # Load Existing Feature Profile
        if not user.feature_profile:
            self.db_features = Features()
        else:
            self.db_features = user.feature_profile

        # Counts of feature combinations
        self.fc = self.db_features.unidict

        # Counts of categories
        self.cc = self.db_features.dircount

        # Counts of documents in each category
        self.getfeatures = getfeatures

    # Increase the count of a feature/category pair
    def incf(self, f, cat):
        self.fc.setdefault(f, {})
        self.fc[f].setdefault(cat, 0)
        self.fc[f][cat] += 1

    # Increase the count of a category
    def incc(self, cat):
        self.cc.setdefault(cat, 0)
        self.cc[cat] += 1
        
    # The number of times a feature has appeared in a category
    def fcount(self, f, cat):
        if f in self.fc and cat in self.fc[f]:
            return float(self.fc[f][cat])
        return 0.0

    # The number of items in a category
    def catcount(self, cat):
        if cat in self.cc:
            return float(self.cc[cat])
        return 0

    # The total number of items
    def totalcount(self):
        return sum(self.cc.values())

    # The list of all categories
    def categories(self):
        return self.cc.keys()
    
    # Calculate weighted probabilities
    def weightedprob(self, f, cat, prf, weight=1.0, ap=0.5):
        # Calculate current probability
        basicprob = prf(f,cat)

        # Count the how often this feature has appeared in all categories
        totals = sum([self.fcount(f,c) for c in self.categories()])

        # Calculate the weighted average
        bp = ((weight * ap) + (totals * basicprob)) / (weight + totals)
        return bp

    
    # Calculate probabilities
    def fprob(self, f, cat):
        if self.catcount(cat) == 0: return 0
        # The total number of times this feature appeared in this
        # category divided by the total number of items in this category
        return self.fcount(f,cat)/self.catcount(cat)
    
    def train(self, item, cat):
        features = self.getfeatures(item, self.stopwords)
        # Increment the count for every feature with this category
        for f in features:
            self.incf(f,cat)

        # Increment the count for this category
        self.incc(cat)
        
        # Save updated Features Set to Datastore
        self.db_features.put()
        if not self.user.feature_profile:
            self.user.feature_profile = self.db_features.key()
            self.user.put()

            
class naivebayes(classifier):
  
  def __init__(self, user, getfeatures):
    classifier.__init__(self, user, getfeatures)
    self.thresholds = {}
  
  def docprob(self, item, cat):
    features = self.getfeatures(item, self.stopwords)   

    # Multiply the probabilities of all the features together
    p = 1
    for f in features:
        p *= self.weightedprob(f, cat, self.fprob)
    return p

  def prob(self, item, cat):
    catprob = self.catcount(cat) / self.totalcount()
    docprob = self.docprob(item, cat)
    return docprob * catprob
  
  
  def setthreshold(self, cat, t):
    self.thresholds[cat] = t

  def getthreshold(self, cat):
    if cat not in self.thresholds:
        return 1.0
    return self.thresholds[cat]
  
  def classify(self, item, default=None):
    probs = {}
    # Find the category with the highest probability
    max = 0.0
    for cat in self.categories():
      probs[cat] = self.prob(item, cat)
      if probs[cat] > max: 
        max = probs[cat]
        best = cat

    # Make sure the probability exceeds threshold * next best
    for cat in probs:
      if cat == best:
          continue
      if probs[cat] * self.getthreshold(best) > probs[best]:
          return default
    return best


    
class Judge(webapp.RequestHandler):
    def get(self):
        # Load user
        user = users.get_current_user()
        user = db.GqlQuery("SELECT * FROM User WHERE user_id = '%s'" % user.user_id()).get()

        # Load story
        key = self.request.get("key")
        story = db.get(key)
        
        # Which direction was clicked?
        dir = str(self.request.get("dir"))
        up = True if dir == 'up' else False

        print ''
        print 'TEST STUFF\n---------\n\n'

        cl = naivebayes(user, getwords)

        for x in range(10):
            cl.train('blah','down')

        print cl.classify('blah')
        print cl.prob('blah','down')


        cl.train('Nobody owns the water.','good')
        cl.train('the quick rabbit jumps fences','good')
        cl.train('buy pharmaceuticals now','bad')
        cl.train('make quick money at the online casino','bad')
        cl.train('the quick brown fox jumps','good')
        cl.setthreshold('bad', 2.0)
        

        print ''
        print 'dicts: %s' %user.feature_profile.unidict
        print ''
        print 'dircount: %s' %user.feature_profile.dircount

        print cl.classify('quick rabbit', default='unknown')
        print cl.classify('quick money', default='unknown')
        print cl.classify('quick money', default='unknown')
        print cl.classify('quick money', default='unknown')
        print ''
        
        # Load N-Grams
        #words = getwords(story, stopwords)
        #ngrams = countwords(words)

        '''
        def countwords(words):
            # Count unigrams
            uni_freq_dict = {}
            for word in words:
                uni_freq_dict[word] = uni_freq_dict.get(word,0) + 1

            # Break down into bigrams
            bigrams = []
            for index, x in enumerate(words):
                if (index + 1) < len(words):
                    bigrams.append((x, words[index + 1]))

            # Count bigrams
            bi_freq_dict = {}
            for b in bigrams: bi_freq_dict[b] = bi_freq_dict.get(b,0) + 1

            return {'uni': uni_freq_dict,
                    'bi': bi_freq_dict}
        '''
        """
        # Store the story key
        features.stories.setdefault(dir, [])
        features.stories[dir].append(story.key())

        denom = features.dircount[dir]
        
        for word in ngrams['uni']:

            # Add unigram counts
            self.increaseCount(unidict, word, dir)
        
            
            '''
            # Re-Calc probabilities
            if key in uniprob:
                features.uniprob[key] = features.uniprob[key] + log(1.0/denom)
            else:
                features.uniprob[key] = log(1.0/denom)
            '''

        '''
        # Add bigram counts and recalc probabilities
        for key in ngrams['bi']:
            bidict[key] = bidict.get(key,0) + 1
            if key in biprob:
                biprob[key] = biprob[key] + log(1.0/denom)
            else:
                biprob[key] = log(1.0/denom)
        '''
        
        # Save updated Features Set to Datastore
        features.put()
        if not user.feature_profile:
            user.feature_profile = features.key()
            user.put()
        
        print ''
        print 'COUNTS'
        print features.dircount

        print ''
        print 'STORIES'
        print [(dir, len(dir)) for dir in features.stories]
        
        print ''
        print 'DICTS'
        print '-------------------------\n'
        for i in features.unidict:
            print i, unidict[i]

        print ''
        print 'PROBABILITIES'
        print '-------------------------\n'
        for i in features.uniprob:
            print i, uniprob[i]
        print ''

        #for key,value in features.down_bigram_prob.iteritems():
        #    print '%s: %s' %(key, value)
        #print '\n'

        #for key,value in features.up_bigram_prob.iteritems():
        #    print '%s: %s' %(key, value)
        #print ''

        #self.redirect('/')
        """ 
class MainPage(webapp.RequestHandler):
    '''
    def classify(self, features):
        posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 100")
        good_posts = []
        for post in posts:
            ngrams = getwords(post)
            downprob = 0.0
            upprob = 0.0
            for n in ngrams['uni']:
                if n in features.up_unigram_prob:
                    upprob += features.up_unigram_prob[n]
                    #self.response.out.write('UP: %s : %s<BR>' %(n, features.up_unigram_prob[n]))
                if n in features.down_unigram_prob:
                    downprob += features.down_unigram_prob[n]
                    #self.response.out.write('DOWN: %s : %s<BR>' %(n, features.down_unigram_prob[n]))

            ##
            # Weight bigrams 2x as much as unigrams?
            ##
                    
            if fabs(downprob) - fabs(upprob) <= 0:
                if fabs(upprob) > 0:
                    self.response.out.write('<i><b>%s</b></i><br>' %post.title)
                    good_posts.append(post)
                else:
                    self.response.out.write('%s<br>' %post.title)
            else:
                self.response.out.write('<font color="#ddd">%s</font><br>' %post.title)
            #self.response.out.write('ID: %s | UP: %s | DOWN: %s<br>' %(post.hn_id, upprob, downprob))
        #return good_posts
    '''
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

            #if not user.feature_profile:
            posts = db.GqlQuery("SELECT * FROM Node ORDER BY points DESC LIMIT 100")
            #else:
            #    posts = self.classify(user.feature_profile)
                
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
            for x in range(10):
                req = url + '&start=%s' % (x * 100)
                logging.info('URL - %s' %req)
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
