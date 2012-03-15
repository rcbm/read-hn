import re
from logging import info as log
from google.appengine.ext import db
from google.appengine.api import users
from models import *


# Get words (unigrams)
def getwords(text, stopwords):
    # Split the words by non-alpha characters
    words = [s.lower() for s in re.compile('\\W*').split(text)
             if len(s) > 2 and len(s) < 20]

    # Remove stop words
    words = [w for w in words if w not in stopwords]

    return dict([(w, 1) for w in words])

# Get word pairs (bigrams)
def getpairs(text, stopwords):
    words = getwords(text, stopwords).keys()
    pairs = []
    for i, x in enumerate(words):
        if (i + 1) < len(words):
            pairs.append((x, words[i + 1]))
            
    return dict([(p, 1) for p in pairs])

class classifier:
    def __init__(self, user, getfeatures):
        self.user = user

        # Load stopwords
        self.stopwords = [str(x.word) for x in db.GqlQuery("SELECT * FROM StopWord").fetch(1000)]

        # Load Existing Feature Profile
        #self.db_features = user.features
        
        # Counts of feature combinations
        self.fc = self.user.fdict

        # Counts of categories
        self.cc = self.user.catcount

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
    best = default
    max = 0.0
    for cat in self.categories():
      probs[cat] = self.prob(item, cat)
      if probs[cat] > max: 
        max = probs[cat]
        best = cat

    log('Feature: "%s" | Probs: %s' %(item,probs))
    # Make sure the probability exceeds threshold * next best
    for cat in probs:
      if cat == best:
          continue
      if probs[cat] * self.getthreshold(best) > probs[best]:
          return default
    return best

  
