#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import jinja2
import re
import logging
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import images
from datetime import datetime
import urllib2
import time
import json


template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.out.write(*a,**kw)
    def render_str(self,template,**params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))

class MainHandler(Handler):
    def get(self):
        data =article.gql("order by created desc limit 1")
        adata = article.gql("order by created desc limit 5 offset 1")
        data2 = article.gql("order by created desc limit 1 offset 1")
        data3 = article.gql("order by created desc limit 1 offset 2")
        data4 = article.gql("order by created desc limit 1 offset 3")
        data5 = article.gql("order by created desc limit 1 offset 4")
        data6 = article.gql("order by created desc limit 1 offset 5")
        
        self.render("Project.html",adata = adata,data = data,data2 =data2,data3 = data3,data4 =data4,data5 = data5,data6 =data6)
    
        
class article(db.Model):
    headline = db.StringProperty(required = True)
    sideheadline = db.StringProperty()
    content = db.TextProperty(required = True)
    created = db.DateProperty(auto_now_add = True)
    author = db.TextProperty()
    picture = db.StringProperty()
    views = db.IntegerProperty(default=0)
    featured = db.IntegerProperty(default = 0)
    
    
    
class WriteFormHandler(Handler):                             
    def get(self):     
        self.render("WriteForm.html")
    def post(self):
        headline = self.request.get("headline").upper()
        content  = self.request.get("content") 
        author   = self.request.get("author")
        sideheadline = self.request.get("sideheadline")
        featured = int(self.request.get("featured"))
        if self.request.get('picture'):
            picture = self.request.get('picture')
        else:
            picture = "/images/default.jpg"
       
        a = article(headline = headline,content =content,author = author,picture = picture,sideheadline = sideheadline,featured = featured)
         
        a.put();
        self.redirect('/news')

class TeamsHandler(Handler):
    def get(self):
        self.render("teams.html")
class ArticleHandler(Handler):
    def get(self,post_id):
        data = article.get_by_id(int(post_id))
        data.views = data.views + 1
        data.put()
        adata = article.gql("order by views desc limit 6")
        url = self.request.url
        host = self.request.host
        self.render("NewsTemplate.html",adata = adata,data = data,url = url, host = host)
        
class AboutHandler(Handler):
    def get(self):
        self.render("About.htm")
class RSSHandler(Handler):
    def get(self):
        self.render("rssfeeds.html")
class TeamsheetHandler(Handler):
    def get(self):
        self.render("Teamsheet.html")
class NewsHandler(Handler):
    def get(self):
        adata = article.gql("order by created desc")
        data  = article.gql("order by created desc limit 6")
        self.render("news.html",adata = adata,data = data)
    def post(self):
        date1 = self.request.get("datebox")
        sortype = self.request.get("sorting")
        
        if date1 == "":
            date1 = "2016-01-01"
        dateobj = datetime.strptime(date1, '%Y-%m-%d')
        x = "where created >= DATE('" + date1 + "')" +  " order by " + sortype
        adata = article.gql(x)
        data  = article.gql("order by created desc limit 6")
        self.render("news.html",adata = adata,data = data)
class RSSplHandler(Handler):
    def get(self):
        self.render("premierleaguerss.html")
class RSSuclHandler(Handler):
    def get(self):
        self.render("Championsleaguerss.html")
class RSSIntHandler(Handler):
    def get(self):
        self.render("InternationalFootball.html")
class LiveScoreHandler(Handler):
    def get(self):
        self.render("Livescores.html")
class fbHandler(Handler):
    def get(self):
        self.render("fbtest.html")
        
class PopularNewsHandler(Handler):
    def get(self):
        data = article.gql(' where featured = 1 order by created desc limit 1 ')
        adata = article.gql('where featured = 1 order by created desc limit 5 offset 1')
        allfeatured = article.gql(' where featured = 1 order by created desc limit 6')
        popular = article.gql(' order by views desc limit 12')
        latest  = article.gql(' order by created desc limit 6')
        self.render("mostread.html",adata = adata,data =data,allfeatured = allfeatured,popular = popular,latest = latest)



app = webapp2.WSGIApplication([
    ('/', MainHandler),('/teams',TeamsHandler),('/about',AboutHandler),('/teamsheet',TeamsheetHandler),('/article',WriteFormHandler),('/news',NewsHandler),('/allnews',RSSHandler),('/uclnews',RSSuclHandler),('/Internationalnews',RSSIntHandler),('/eplnews',RSSplHandler),('/livescores',LiveScoreHandler),('/popular',PopularNewsHandler),(r'/news/(\d+)',ArticleHandler),('/fb',fbHandler)], debug=True)
