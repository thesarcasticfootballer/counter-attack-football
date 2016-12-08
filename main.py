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
#SAMEER PASHA
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
            piclink = self.request.get('picture')
            tempvar="upload/c_scale,q_auto:good,w_1600"
            picture =piclink.replace('upload',tempvar)
        else:
            picture = "/images/default.jpg"
       
        a = article(headline = headline,content =content,author = author,picture = picture,sideheadline = sideheadline,featured = featured)
         
        a.put();
        memcache.delete('home')
        memcache.delete('popular')
        self.redirect('/')


class HomeHandler(Handler):
  def get(self):
        content = self.cache('homepage')
        if content:
                   data = content['data']
                   adata = content['adata']
                   bdata = content['bdata']
                   cdata = content['cdata']
                   ddata = content['ddata']
        else:
            data = list(article.gql('  order by created desc limit 1 '))
            adata = list(article.gql(' order by created desc limit 2 offset 8'))
            bdata = list(article.gql(' order by created desc limit 2 offset 10'))
            cdata = list(article.gql(' order by created desc limit 6 offset 1'))
            ddata = list(article.gql('  order by created desc limit 1 offset 7'))
            content = {'data':data,'adata':adata,'bdata':bdata,'cdata':cdata,'ddata':ddata}
            memcache.add(key='homepage',value=content,time=3600)
        self.render("Homepage.html",adata = adata,data =data,bdata = bdata,cdata =cdata,ddata=ddata)

        



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
                 
            
class NewsArticleHandler(Handler):
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
        self.response.set_cookie('vote',"success",path='/article/'+ post_id,expires=d)
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
            adata = list(article.gql("order by created desc limit 6"))
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
        self.render("articletemplate.html",adata = adata,data = data,url = url, host = host, yes=up, no=(total-up))



class DisplayallHandler(Handler):
    def get(self):
        data = list(article.gql("order by created desc limit 10"))
        self.render("pagination.html",data=data)



app = webapp2.WSGIApplication([
        ('/article',WriteFormHandler),('/',HomeHandler),
  
    (r'/news/(\d+)',NewsArticleHandler),
    ('/signin/google',GSigninHandler),('/signin/fb',FBSigninHandler),
    ('/move', MoveDBHandler),('/all',DisplayallHandler)], debug=False)
