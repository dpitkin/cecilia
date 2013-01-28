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

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

def render_template(handler_object, file_name, template_values):
  user = users.get_current_user()
  template_values['user'] = user
  template_values['logout_url'] = users.create_logout_url('/')
  template_values['login_url'] = users.create_login_url(handler_object.request.uri)
  template = jinja_environment.get_template(file_name)
  handler_object.response.out.write(template.render(template_values))
  
class Thread(db.Model):
  title = db.StringProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  recipient_id = db.IntegerProperty()
  #has_many messages
  #belongs_to User
  created_by_id = db.StringProperty()
  
class Message(db.Model):
  body = db.TextProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  #belongs_to Thread
  
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