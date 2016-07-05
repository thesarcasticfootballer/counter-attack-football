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
import datetime
import urllib2
import time
import json
from google.appengine.api import memcache
import cgi

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


CLIENT_ID = "636222690890-s7qdqru8kkk7v349r333i74q2a01btk5.apps.googleusercontent.com"
FB_ID = "945733035525846|e4017e80ce68c389ebcc98ba625b9b46"
FB_APP = '945733035525846'


class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.out.write(*a,**kw)
    def render_str(self,template,**params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))
    def cache(self, key):
        return memcache.get(key)


class MainHandler(Handler):
    def get(self):
        content = self.cache('home')
        if content:
            data = content['data']
            adata = content['adata']
            hot = content['hot']
            newnotfeat = content['newnotfeat']
            newfeat = content['newfeat']
            newfeat1 = content['newfeat1']
            newfeat2 = content['newfeat2']
            newfeat3 = content['newfeat3']
        else:
            data =list(article.gql("order by created desc limit 1"))
            adata = list(article.gql("order by created desc limit 6 "))
            hot = list(article.gql("order by views desc limit 1 "))
            newnotfeat = list(article.gql("where featured = 0 order by created desc limit 3 "))
            newfeat = list(article.gql("where featured = 1 order by created desc limit 1 "))
            newfeat1 = list(article.gql("where featured = 1 order by created desc limit 1 offset 1"))
            newfeat2= list(article.gql("where featured = 1 order by created desc limit 1 offset 2"))
            newfeat3 = list(article.gql("where featured = 1 order by created desc limit 2 offset 3 "))    
            content = {'data':data,'adata':adata,'hot':hot,'newnotfeat':newnotfeat,'newfeat':newfeat,'newfeat1':newfeat1,'newfeat2':newfeat2,'newfeat3':newfeat3}
            memcache.add(key="home", value=content, time=3600)
        self.render("Project.html",adata = adata,data = data,hot=hot,newnotfeat =newnotfeat,newfeat=newfeat,newfeat1=newfeat1,newfeat2=newfeat2,newfeat3=newfeat3)
    
        
class article(db.Model):
    headline = db.StringProperty(required = True)
    sideheadline = db.StringProperty()
    content = db.TextProperty(required = True)
    created = db.DateProperty(auto_now_add = True)
    author = db.TextProperty()
    picture = db.StringProperty()
    views = db.IntegerProperty(default=0)
    featured = db.IntegerProperty(default = 0)
    total = db.IntegerProperty(default = 0)
    up = db.IntegerProperty(default = 0)
    
    
    
    
class WriteFormHandler(Handler):                             
    def get(self):     
        self.render("WriteForm.html")
    def post(self):
        headline = self.request.get("headline")
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
        memcache.delete('home')
        memcache.delete('popular')
        self.redirect('/news')

class TeamsHandler(Handler):
    def get(self):
        self.render("teams.html")
class ArticleHandler(Handler):
    def post(self, post_id):
        data = article.get_by_id(int(post_id))
        if memcache.get(post_id+"total") == None:
            if data.total == 0:
                memcache.add(key=post_id+"total", value=0, time = 3600)
                memcache.add(key=post_id+"up", value=0, time = 3600)
            else:
                memcache.add(key=post_id+"total", value=data.total, time = 4000)
                memcache.add(key=post_id+"up", value=data.up, time = 4000)
        memcache.incr(post_id+"total")
        value = int(self.request.get("value"))
        if value == 1:
            memcache.incr(post_id+"up")
        d = datetime.datetime.now()
        d = d + datetime.timedelta(30) 
        total = memcache.get(post_id+"total")
        up = memcache.get(post_id+"up")
        ans = "%s,%s" % (up,(total-up))
        self.response.set_cookie('vote',"success",path='/news/'+ post_id,expires=d)
        self.response.out.write(ans)

    def get(self,post_id):
        content = self.cache(post_id)
        if content:
            data = content['data']
            adata = content['adata']
        else:
            data = article.get_by_id(int(post_id))
            #data.views = data.views + 1
            #data.put()
            adata = list(article.gql("order by views desc limit 6"))
            content = {'data':data,'adata':adata}
            memcache.add(key=post_id, value=content, time=4000)
        views = self.cache(post_id+'views')
        if not views:
            memcache.add(key=post_id+'views',value=data.views,time=4000)
        memcache.incr(post_id+'views')
        url = self.request.url
        host = self.request.host
        if memcache.get(post_id+"total"):
            total = memcache.get(post_id+"total")
            up = memcache.get(post_id+"up")
        else:
            total = data.total
            if total == 0:
                up = 0
            else:
                up = data.up
        self.render("NewsTemplate.html",adata = adata,data = data,url = url, host = host, yes=up, no=(total-up))
        
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
        adata = article.gql("order by created desc limit 10")
        data  = article.gql("order by created desc limit 6")
        self.render("news.html",adata = adata,data = data)
    def post(self):
        date1 = self.request.get("datebox")
        sortype = self.request.get("sorting")  
        if date1 == "":
            date1 = "2016-01-01"
        dateobj = datetime.datetime.strptime(date1, '%Y-%m-%d')
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
        content = self.cache('popular')
        if content:
            data = content['data']
            adata = content['adata']
            allfeatured = content['allfeatured']
            breaking = content['breaking']
            popular = content['popular']
            latest = content['latest']
        else:
            data = list(article.gql(' where featured = 1 order by created desc limit 1 '))
            adata = list(article.gql('where featured = 1 order by created desc limit 5 offset 1'))
            allfeatured = list(article.gql(' where featured = 1 order by created desc limit 6'))
            breaking = list(article.gql("order by created desc limit 10  "))
            popular = list(article.gql(' order by views desc limit 12'))
            latest  = list(article.gql(' order by created desc limit 6'))
            content = {'data':data,'adata':adata,'allfeatured':allfeatured,'breaking':breaking,'popular':popular,'latest':latest}
            memcache.add(key='popular',value=content,time=3600)
        self.render("mostread.html",adata = adata,data =data,allfeatured = allfeatured,popular = popular,latest = latest,breaking = breaking)


class GSigninHandler(Handler):
    def get(self):
        userid = self.request.cookies.get('name')
        memcache.delete(userid)
        self.response.out.write('server cache deleted')
    def post(self):
        token = self.request.get('idtoken')
        gurl = "https://www.googleapis.com/oauth2/v3/tokeninfo?id_token="
        check = urllib2.urlopen(gurl+token)
        if check.getcode() == 200:
            user = json.loads(check.read())
            try:
                if user["aud"] != CLIENT_ID:
                    raise "Invalid!!"
                if user['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise "Invalid!!"
                if user['exp'] < time.time():
                    raise "Invalid!!"
                self.response.set_cookie('name',user['sub'],path='/')
                self.response.out.write(user['given_name'])
                memcache.add(key = user['sub'], value = user, time=3600)
            except "Invalid!!":
                self.response.out.write("not valid")
                


class FBSigninHandler(Handler):
    def post(self):
        token = self.request.get("accesstoken")
        fburl = "https://graph.facebook.com/debug_token?input_token="+token+"&access_token="
        check = urllib2.urlopen(fburl+FB_ID)
        if check.getcode() == 200:
            user = json.loads(check.read())
            try:
                if user['data']['expires_at'] < time.time():
                    raise "Invalid!!"
                if user['data']['is_valid'] == False:
                    raise "Invalid!!"
                if user['data']['app_id'] != FB_APP:
                    raise "Invalid!!"
                self.response.set_cookie('name',user['data']['user_id'],path='/')
                self.response.out.write("registered at server side")
                memcache.add(key = user['data']['user_id'], value = user, time=3600)
            except "Invalid!!":
                self.response.out.write("not valid")


class MoveDBHandler(Handler):
    def get(self):
        keys = article.all(keys_only =True)
        for k in keys:
            #data = article.get_by_id(k.id())
            #url = data.picture
            #url = url.replace('/q_auto','',1)
            #url = url.replace('upload/','upload/q_auto/',1)
            #data.picture = url
            #data.put()
            total = memcache.get(str(k.id())+"total")
            views = memcache.get(str(k.id())+"views")
            if total or views:
                data = article.get_by_id(k.id())
                if (total > data.total):
                    data.total = total
                    data.up = memcache.get(str(k.id())+"up")
                    #memcache.delete(str(k.id())+"total")
                    #memcache.delete(str(k.id())+"up")
                if (views > data.views):
                    data.views = views
                    #memcache.delete(str(k.id())+"views")
                data.put()
        memcache.flush_all()
                
                                                                                                                                                                                    
            



app = webapp2.WSGIApplication([
    ('/', MainHandler),('/teams',TeamsHandler),
    ('/about',AboutHandler),('/teamsheet',TeamsheetHandler),
    ('/article',WriteFormHandler),('/news',NewsHandler),
    ('/allnews',RSSHandler),('/uclnews',RSSuclHandler),
    ('/Internationalnews',RSSIntHandler),('/eplnews',RSSplHandler),
    ('/livescores',LiveScoreHandler),('/popular',PopularNewsHandler),
    (r'/news/(\d+)',ArticleHandler),('/fb',fbHandler),
    ('/signin/google',GSigninHandler),('/signin/fb',FBSigninHandler),
    ('/move', MoveDBHandler)], debug=False)
