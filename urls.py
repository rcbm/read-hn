#from google.appengine.dist import use_library
#use_library('django', '1.2')

import os
from main import *
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/scrape', Scrape),
                                      ('/vote', Judge)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
