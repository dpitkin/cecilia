#!/usr/bin/env python

import database
from database import db
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
      if li.count() > 0:
        li = li.get()
        if li.first_name == "" or li.last_name == "" or li.nickname == "": #if not valid user, don't create a new li but allow them to visit the page
          li.create_xsrf_token()
          database.render_template(self, '/users/register_user.html', {})
        else: #if they're a valid user, they can't re-register
          self.redirect('/')
      else: #create a brand new li
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
        if user.email() == 'hardcodetest1@gmail.com' or user.email() == 'hardcodetest2@gmail.com':
          li.is_admin = True
        else:
          li.is_admin = database.users.is_current_user_admin()
        li.desc = cgi.escape(self.request.get('desc'))
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
      li.email = user.email()
      li.nickname = cgi.escape(self.request.get('nickname'))
      li.private = bool(self.request.get('private'))
      li.desc = cgi.escape(self.request.get('desc'))
      if(self.request.get('avatar')):
        li.avatar = database.db.Blob(database.images.resize(self.request.get('avatar'), 128, 128))
      li.put()
      database.logging.info("Updating LoginInformation. Info: \nFirst name: %s\nLast Name: %s\nUserID: %s\n",
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
      # delete messages
      messages = database.db.GqlQuery("SELECT * FROM Message WHERE created_by_id = :1", user.user_id())
      for m in messages:
        database.db.delete(m)
      # delete threads
      threads = database.db.GqlQuery("SELECT * FROM Thread WHERE created_by_id = :1", user.user_id())
      for t in threads:
        database.db.delete(t)
      # delete user_feedback
      user_feedback = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE created_by_id = :1", user.user_id())
      for f in user_feedback:
        database.db.delete(f)
      # delete item_feedback
      item_feedback = database.db.GqlQuery("SELECT * FROM ItemFeedback WHERE created_by_id = :1", user.user_id())
      for f in item_feedback:
        database.db.delete(f)
      #delete the li
      li = database.get_current_li()
      database.logging.info("Deleting LoginInformation user_id=%s", li.user_id)
      database.db.delete(li)
      self.redirect(database.users.create_logout_url('/'))
    else:
      self.redirect('/')
      
class UserFeedbackHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      f = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE for_user_id = :1 AND created_by_id = :2", cgi.escape(self.request.get('for_user_id')), user.user_id())
      if f.count() == 0 and cgi.escape(self.request.get('for_user_id')) != user.user_id(): #can only rate a seller once and you can't rate yourself
        user_feedback = database.UserFeedback()
        user_feedback.created_by_id = user.user_id()
        user_feedback.for_user_id = cgi.escape(self.request.get('for_user_id'))
        user_feedback.rating = int(cgi.escape(self.request.get('rating')))
        user_feedback.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
    
class ListUserFeedback(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      feedback = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE for_user_id = :1", cgi.escape(self.request.get('user_id')))
      li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      database.get_current_li().create_xsrf_token();
      back_url = self.request.referer
      database.render_template(self, '/users/list_user_feedback.html', {'feedback': feedback, 'li': li, 'back_url': back_url})
    else:
      self.redirect('/')
      
class DeleteUserFeedback(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      feedback_id = cgi.escape(self.request.get('feedback_id'))
      f = db.get(db.Key.from_path('UserFeedback', int(feedback_id)))
      db.delete(f)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
    
app = database.webapp2.WSGIApplication([('/users/', MainHandler), ('/users/verify_user/', RegisterHandler), 
('/users/save_user', SaveLIHandler), ('/users/delete_user', DeleteHandler), ('/users/update_user', UpdateLIHandler),
('/users/submit_feedback', UserFeedbackHandler), ('/users/list_user_feedback',ListUserFeedback), ('/users/delete_user_feedback', DeleteUserFeedback)], debug=True)