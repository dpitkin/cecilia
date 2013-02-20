#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import logging

import string
import hashlib
import random
import time
import datetime

import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import images

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

def render_template(handler_object, file_name, template_values):
  user = users.get_current_user()
  if user:
    current_li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id()).get()
  else:
    current_li = None
  template_values['current_li'] = current_li
  template_values['user'] = user
  template_values['logout_url'] = users.create_logout_url('/')
  template_values['login_url'] = users.create_login_url('/users/verify_user/')
  template_values['is_admin'] = current_li.is_admin
  if user:
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id()).get()
    template_values['unread_messages'] = db.GqlQuery("SELECT * FROM Message WHERE recipient_id = :1 AND read = :2", user.user_id(), False).count()
    if li and not(li.is_active):
      file_name = '/users/inactive_notification.html'
  #check to make sure they've registered (and check for infinite redirects)
  if user and string.find(handler_object.request.uri, '/users/verify_user/') == -1 and current_li and (current_li.first_name == "" or current_li.last_name == "" or current_li.nickname == ""):
    handler_object.redirect('/users/verify_user/')
  else: 
    template = jinja_environment.get_template(file_name)
    handler_object.response.out.write(template.render(template_values))
  
def get_current_li():
  if users.get_current_user():
    return db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", users.get_current_user().user_id()).get()
  return None
  
class LoginInformation(db.Model):
  first_name = db.StringProperty()
  last_name = db.StringProperty()
  #belongs_to User
  user_id = db.StringProperty()
  is_active = db.BooleanProperty()
  is_admin = db.BooleanProperty()
  avatar = db.BlobProperty()
  nickname = db.StringProperty()
  private = db.BooleanProperty()
  xsrf_token = db.StringProperty()
  
  def display_avatar(this):
    if this.avatar:
      return '<img src="/images/?avatar_id=' + this.user_id + '"/>'
  
  def get_private_display_name(this):
    return this.first_name + " " + this.last_name
  
  def get_public_display_name(this):
    return this.nickname
    
  def get_display_name(this):
    li = get_current_li()
    if (this.private == False) or (li and this.user_id == li.user_id):
      return this.get_private_display_name()
    else:
      return this.get_public_display_name()
    
    
  def create_xsrf_token(this):
    #create a token based off of their name, random number, id, and time, then hash via sha512
    #won't scale too great, but should be pretty secure
    this.xsrf_token = hashlib.sha512(str(random.random()) + this.last_name + str(this.key()) + this.first_name + str(time.clock())).hexdigest()
    this.put()
    
  def verify_xsrf_token(this, request):
    #change the token to make it obsolete
    old_token = this.xsrf_token
    this.xsrf_token = hashlib.sha512(this.xsrf_token).hexdigest()
    this.put()
    if old_token == request.request.get('xsrf_token'):
      return True
    else:
      return False
      
  def get_average_rating(this):
    #grab all ratings
    ratings = db.GqlQuery("SELECT * FROM UserFeedback WHERE for_user_id = :1", this.user_id)
    total = 0
    for r in ratings:
      total += r.rating
    if(ratings.count() > 0):
      return '%.2f' % float(float(total)/float(ratings.count()))
    else:
      return None
  
class Thread(db.Model):
  title = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  recipient_id = db.StringProperty()
  #has_many messages
  #belongs_to User
  created_by_id = db.StringProperty()
  item_details = db.StringProperty()
  
class Message(db.Model):
  body = db.TextProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  created_by_id = db.StringProperty()
  recipient_id = db.StringProperty()
  read = db.BooleanProperty()
  #belongs_to Thread
  def get_sender(this):
    return db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", this.created_by_id).get()
  
def save_message(message, thread, user):
  message.parent = thread
  message.put()

class Item(db.Model):
  title = db.StringProperty()
  description = db.TextProperty()
  summary = db.TextProperty()
  price = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  expiration_date = db.DateProperty()
  image = db.BlobProperty()
  is_active = db.BooleanProperty()
  feedback = db.TextProperty()
  rating = db.IntegerProperty()
  buyer_id = db.StringProperty()
  #belongs_to User
  created_by_id = db.StringProperty()

  def is_expired(this):
    return (datetime.date.today() > this.expiration_date)

  def display_image(this):
    if this.image:
      return '<img src="/images/?item_id=' + str(this.key().id()) + '"/>'
    else:
      return ''
    
  def get_creator(this):
    return db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", this.created_by_id).get()
      
class UserFeedback(db.Model):
  created_by_id = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  for_user_id = db.StringProperty()
  rating = db.IntegerProperty()
  
class ItemFeedback(db.Model):
  created_by_id = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  item_id = db.StringProperty()
  rating = db.IntegerProperty()
  feedback = db.TextProperty()
  
class Search(db.Model):
  created_by_id = db.StringProperty()
  search = db.StringProperty()