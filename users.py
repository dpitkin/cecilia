#!/usr/bin/env python

import database

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      li = database.get_current_li()
      li.create_xsrf_token()
      database.render_template(self, '/users/index.html', {'li': li})
    else:
      self.redirect('/')

class RegisterHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
      if li.count() == 1:
        self.redirect('/')
      else:
        li = database.LoginInformation(first_name="",last_name="", user_id=user.user_id(), is_active=True)
        li.put()
        li.create_xsrf_token()
        database.render_template(self, '/users/register_user.html', {})
    else:
      self.redirect('/')
      
class SaveLIHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
    #check for duplicates
    if user and li.count() == 1:
      li = database.get_current_li()
      if li.verify_xsrf_token(self):
        li.first_name = cgi.escape(self.request.get('first_name'))
        li.last_name = cgi.escape(self.request.get('last_name'))
        li.nickname = cgi.escape(self.request.get("nickname"))
        li.private = bool(self.request.get("private"))
        li.is_active = True
        li.is_admin = database.users.is_current_user_admin()
        if(self.request.get('avatar')):
          li.avatar = database.db.Blob(database.images.resize(self.request.get('avatar'), 128, 128))
        li.put()
        database.logging.info("Saving new LoginInformation. Info:\nFirst name: %s\nLast Name: %s\nUserID: %s\nAdmin: %s\n",
        li.first_name, li.last_name, li.user_id, li.is_admin)
    self.redirect('/')
    
class UpdateLIHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      li = database.get_current_li()
      li.first_name = cgi.escape(self.request.get('first_name'))
      li.last_name = cgi.escape(self.request.get('last_name'))
      li.nickname = cgi.escape(self.request.get('nickname'))
      li.private = bool(self.request.get('private'))
      if(self.request.get('avatar')):
        li.avatar = database.db.Blob(database.images.resize(self.request.get('avatar'), 128, 128))
      li.put()
      database.logging.info("Updating LoginInformation. Info: \nFirst name: %s\nLast Name: %s\n%UserID: %s\n",
      li.first_name, li.last_name, li.user_id)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
    
class DeleteHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      #delete all the items
      items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id())
      for item in items:
        database.db.delete(item)
      #delete the li
      li = database.get_current_li()
      database.db.delete(li)
      self.redirect(database.users.create_logout_url('/'))
    else:
      self.redirect('/')
    
    
app = database.webapp2.WSGIApplication([('/users/', MainHandler), ('/users/verify_user/', RegisterHandler), 
('/users/save_user', SaveLIHandler), ('/users/delete_user', DeleteHandler), ('/users/update_user', UpdateLIHandler)], debug=True)