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

import cgi

import hashlib
import random

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class User(db.Model):
  first_name = db.StringProperty()
  last_name = db.StringProperty()
  #has_many threads
  #has_many items
  is_admin = db.BooleanProperty()
  salt = db.StringProperty()
  hashed_password = db.StringProperty()
  login = db.StringProperty()
def save_user(user, plain_password):
  user.salt = str(random.random())
  user.is_admin = False
  user.hashed_password = hashlib.sha512(plain_password + user.salt).hexdigest()
  user.put()
  
class Thread(db.Model):
  title = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  recipient_id = db.IntegerProperty()
  #has_many messages
  #belongs_to User
  def save_thread(user):
    self.parent = user
    self.put()
  
class Message(db.Model):
  body = db.TextProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  #belongs_to Thread
  def save_message(thread, user):
    self.parent = thread
    self.parent = user
    self.put()

class Item(db.Model):
  title = db.StringProperty()
  description = db.TextProperty()
  price = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  expiration_date = db.DateProperty()
  #belongs_to User
  def save_item(user):
    self.parent = user
    self.put()