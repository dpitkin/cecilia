#!/usr/bin/env python

import database

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", database.users.get_current_user().user_id()).get()
    database.render_template(self, '/users/index.html', {'li': li})

class RegisterHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
    if li.count() == 1:
      self.redirect('/')
    else:
      database.render_template(self, '/users/register_user.html', {})
      
class SaveLIHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
    #check for duplicates
    if li.count() == 0:
      li = database.LoginInformation()
      li.first_name = cgi.escape(self.request.get('first_name'))
      li.last_name = cgi.escape(self.request.get('last_name'))
      li.user_id = user.user_id()
      li.is_active = True
      li.put()
    self.redirect('/')
    
class DeleteHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    #delete all the items
    items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id())
    for item in items:
      database.db.delete(item)
    #delete the li
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id()).get()
    database.db.delete(li)
    self.redirect(database.users.create_logout_url('/'))
    
app = database.webapp2.WSGIApplication([('/users/', MainHandler), ('/users/verify_user/', RegisterHandler), 
('/users/save_user', SaveLIHandler), ('/users/delete_user', DeleteHandler)], debug=True)