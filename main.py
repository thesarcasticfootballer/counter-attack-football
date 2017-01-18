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
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import images
import datetime
import urllib2
import urllib
import time
import json
from google.appengine.api import memcache
import cgi
from google.appengine.ext import ndb
import math

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
							   autoescape=True)


CLIENT_ID = "636222690890-s7qdqru8kkk7v349r333i74q2a01btk5.apps.googleusercontent.com"
FB_ID = "945733035525846|e4017e80ce68c389ebcc98ba625b9b46"
FB_APP = '945733035525846'
ACCESS_TOKEN = u"EAANcI6GihtYBAOylXScCHFJoRgcaIWJoAM4lAlX0CwmuZAISPzwd6J0ZChQUf3Oa7PccWOBuHIOAZCQuUt8KQ6HBCkrgljjQUGRvtHhAKFPkOZBUpeyScJaUZBjfTYrs0HTmH3hShm6fnNIz3cZCTZBA0ca0fA2Jx8ZD"
PAGE_ID = "1029387337137487"




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
	tags = db.StringListProperty()
	
class facts(ndb.Model):
	  picturelink = ndb.StringProperty()
	  facttext = ndb.StringProperty()
	  created = ndb.DateProperty(auto_now_add = True)
	  upvotes = ndb.IntegerProperty(default = 0)
	  tags= ndb.StringProperty(repeated=True)
	  
	 

class polls(ndb.Model):
	  picture = ndb.StringProperty()
	  question= ndb.StringProperty()
	  created = ndb.DateProperty(auto_now_add = True)
	  winner=  ndb.StringProperty()
	  votelist = ndb.StringProperty()
	  
	 
	 
class WriteFormHandler(Handler):                             
	def get(self):     
		self.render("WriteForm.html")
	def post(self):
		headline = self.request.get("headline")
		content  = self.request.get("content") 
		author   = self.request.get("author")
		sideheadline = self.request.get("sideheadline")
		featured = int(self.request.get("featured"))
		tags   = (self.request.get("tags")).split(',')
		if self.request.get('picture'):
			piclink = self.request.get('picture')
			tempvar="upload/c_scale,h_900,q_auto:good,w_1600"
			picture =piclink.replace('upload',tempvar)
		else:
			picture = "/images/default.jpg"  
		a = article(headline = headline,tags = tags,content =content,author = author,picture = picture,sideheadline = sideheadline,featured = featured)  
		key = a.put()
		article_id = key.id()
		memcache.delete(key='homepage')
		#wait for a small duration so that memcache is cleared before it can be reused
		time.sleep(0.1)
		self.redirect('/')

class InstantArticleHandler(Handler):
    def get(self):
        self.render("instant.html")
    def post(self):
        flag = self.request.get("flag")
        article_id = self.request.get("id")
        if flag == '0':
            data = article.get_by_id(int(article_id))
            fb_article = self.render_str("instantarticle.html",data = data,article_id = article_id)
            url = "https://graph.facebook.com/%s/instant_articles" % (PAGE_ID)
            values = {u"access_token":ACCESS_TOKEN,u"html_source":fb_article.encode('utf-8'),u"published":u"true",u"development_mode":u"false"}
            params = urllib.urlencode(values)
            response = urllib2.urlopen(url,data=params)
            msg_to_client = response.read()
            response.close()
        else:
            status_url = "https://graph.facebook.com/%s?access_token=%s" % (article_id,ACCESS_TOKEN)
            response = urllib2.urlopen(status_url)
            msg_to_client = json.loads(response.read())
            response.close()
        self.response.out.write(msg_to_client)


class HomeHandler(Handler):
	def get(self):
		try:
			page = int(self.request.get('page'))
		except ValueError:
			page = 1
		if page > 1:
			data1 = self.goto_page(page)
			data2 = data3 = []
		else:
			content = memcache.get(key='homepage')
			if content is not None:
				data1 = content['data1']
				data2 = content['data2']
				data3 = content['data3']
				popular = content['popular']
			else:
				all_data = list(article.gql(' order by created desc limit 5'))
				data1 = all_data[0:1]
				data2 = all_data[1:3]
				data3 = all_data[3:]
				now = datetime.datetime.now()
				
				popular = list(article.gql('order by views desc limit 4'))
				content = {'data1': data1,'data2': data2,'data3': data3,'popular' : popular}
				memcache.add(key='homepage',value=content,time=3600)
		#total_pages = article.all(keys_only=True).count(100)
		total_entries = memcache.get("total_entries")
		if not total_entries:
			total_entries = 100
		total_pages = math.ceil(total_entries/6.0)
		self.render("Homepage.html",data1 = data1,data2 = data2,data3 = data3,popular = popular, total_pages = int(total_pages), page = int(page))
	def post(self):
		data1 = []
		try:
			page = int(self.request.get('page'))
		except ValueError:
			page = 1
		if page > 1:
			data1 = self.goto_page(page)
		if not data1:
			self.response.out.write("")
		else:
			self.render("pagination.html", data1 = data1)
	def goto_page(self,page):
		# 5 elements per page
		position = (page)*6 -5
		query = " order by created desc limit 6 offset %s" % position
		all_data = list(article.gql(query))
		data1 = all_data
		#self.render("Homepage.html",data1 = data1,data2 = data2,data3 = data3)
		return (data1)
		

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
		keys = list(article.all(keys_only =True))
		total_entries = len(keys)
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
					data.put()
				if (views > data.views):
					data.views = views
					#memcache.delete(str(k.id())+"views")
					data.put()
		memcache.flush_all()
		memcache.add(key="total_entries",value=total_entries,time=4000)
		

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

class FactsHandler(Handler):
	  def get(self):
		   factdata= list(facts.gql(' order by created desc limit 5')) 
		   self.render("facts.html", factdata = factdata)
class FactUploadHandler(Handler):
	  def get(self):
		   self.render("factsupload.html");    	   
	  def post(self):
		  facttext = self.request.get("facttext")
		  tags   = self.request.get("tags")
		  var=[]
		  var=tags.split("#")
		  for i in var:
			if i=='':
				var.remove('')
		  if self.request.get('picturelink'):
			 piclink = self.request.get('picturelink')
			 tempvar="upload//c_scale,h_900,q_auto:good,w_1600"
			 picturelink =piclink.replace('upload',tempvar)
		  else:
			 picturelink = "/images/default.jpg"
		  b = facts(facttext =facttext,tags = var,picturelink = picturelink)	 
		  b.put();
		  self.redirect('/')

  
class PollsHandler(Handler):
  def get(self):
      pollcontent = self.cache('pollpage')
      pdata1 = list(polls.gql('  order by created desc limit 20 '))
      self.render("polls.html",pdata1 = pdata1)

class PollUploadHandler(Handler):
	  def get(self): 
		self.render("pollsupload.html");    
	  def post(self):
		question = self.request.get("question")
		picture  = self.request.get("picture") 
		winner   = self.request.get("winner")
		players = self.request.get("players")  
		votes = self.request.get("votes")  
		p = players.split(',')
		v = votes.split(',')
		total = len(p)
		votelist = {}
		for i in range(0,total):
			k=p[i]
			val = v[i]
			votelist[k]=int(val)
		  
		if self.request.get('picture'):
			piclink = self.request.get('picture')
			tempvar="upload/c_scale,h_900,q_auto:good,w_1600"
			picture =piclink.replace('upload',tempvar)
		else:
			picture = "/images/default.jpg"  
		#votelist = {'Player1': 6, 'Player2': 7, 'Player3': 5} 
		tempvotelist = map(list,votelist.items())
		a=polls(question = question,winner = winner,picture = picture,votelist = json.dumps(tempvotelist))
		a.put();     
		self.redirect('/')
class AboutusHandler(Handler):
  def get(self):
	  self.render("aboutus.html")





app = webapp2.WSGIApplication([
		('/article',WriteFormHandler),('/factupload',FactUploadHandler),('/',HomeHandler),('/pollupload',PollUploadHandler),('/polls',PollsHandler),
	(r'/news/(\d+)',NewsArticleHandler),
	('/signin/google',GSigninHandler),('/signin/fb',FBSigninHandler),
	('/move', MoveDBHandler),('/all',DisplayallHandler),('/facts',FactsHandler),('/aboutus',AboutusHandler),('/instant',InstantArticleHandler)], debug=False)
