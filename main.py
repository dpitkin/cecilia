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
from database import db

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    token = ""
    if database.get_current_li() and database.get_current_li().is_admin:
      token = database.get_current_li().create_xsrf_token()
      items = database.db.GqlQuery("SELECT * FROM Item")
    else:
      items = database.db.GqlQuery("SELECT * FROM Item WHERE expiration_date >= :1 AND is_active = :2 AND deactivated = :3", database.datetime.date.today(), True, False)

    trusted_partners = database.TrustedPartner.all()
    database.render_template(self, 'items/index.html', {'items': items, 'xsrf_token' : token, "partners" : trusted_partners })    
    
class ImageHandler(database.webapp2.RequestHandler):
  def get(self):
    image_id = cgi.escape(self.request.get('avatar_id'))
    item_id = cgi.escape(self.request.get('item_id'))
    if image_id:
      li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", image_id).get()
      if li.avatar:
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(li.avatar)
      else: 
        self.error(404)
    elif item_id:
      item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
      if item.image:
        self.response.headers['Content_type'] = 'image/png'
        self.response.out.write(item.image)
      else:
        self.error(404)
    else:
      li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", database.users.get_current_user().user_id()).get()
      if li.avatar:
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(li.avatar)
      else:
        self.error(404)
    
app = database.webapp2.WSGIApplication([('/', MainHandler), ('/images/', ImageHandler)], debug=True)