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

import hashlib

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
  template_values['is_admin'] = users.is_current_user_admin()
  if user:
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id()).get()
    template_values['unread_messages'] = db.GqlQuery("SELECT * FROM Message WHERE recipient_id = :1 AND read = :2", user.user_id(), False).count()
    if li and not(li.is_active):
      file_name = '/users/inactive_notification.html'
  template = jinja_environment.get_template(file_name)
  handler_object.response.out.write(template.render(template_values))
  
def get_current_li():
  return db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", users.get_current_user.user_id()).get()
  
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
  
  def get_private_display_name(this):
    return this.first_name + " " + this.last_name
  
class Thread(db.Model):
  title = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  recipient_id = db.StringProperty()
  #has_many messages
  #belongs_to User
  created_by_id = db.StringProperty()
  
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
  price = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  expiration_date = db.DateProperty()
  #belongs_to User
  created_by_id = db.StringProperty()