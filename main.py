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

import database

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    database.render_template(self, 'index.html', {})
      
class RegisterHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
    if li.count() == 1:
      self.redirect('/')
    else:
      render_template(self, '/users/register_user.html', {})
      
class SaveLIHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
    #check for duplicates
    if li.count() == 0:
      li = LoginInformation()
      li.first_name = cgi.escape(self.request.get('first_name'))
      li.last_name = cgi.escape(self.request.get('last_name'))
      li.user_id = user.user_id()
      li.is_active = True
      li.put()
    self.redirect('/')
    
app = database.webapp2.WSGIApplication([('/', MainHandler), ('/verify_user', RegisterHandler)], debug=True)