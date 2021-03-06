#!/usr/bin/env python

import database
from database import db
import urllib
import json
from google.appengine.api import urlfetch
cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      li = database.get_current_li()
      token = li.create_xsrf_token()
      database.render_template(self, '/users/index.html', {'li': li, 'xsrf_token' : token, 'partners': database.TrustedPartner.all()})
    else:
      self.redirect('/')

class RegisterHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user.user_id())
      if li.count() > 0:
        li = li.get()
        if li.first_name == "" or li.last_name == "" or li.nickname == "" or li.external_user: #if not valid user or they're external, don't create a new li but allow them to visit the page
          token = li.create_xsrf_token()
          database.render_template(self, '/users/register_user.html', {'new_li': li, 'xsrf_token' : token})
        else: #if they're a valid user, they can't re-register
          self.redirect('/')
      else: #create a brand new li
        li = database.LoginInformation(first_name="",last_name="", user_id=user.user_id(), is_active=True)
        li.put()
        token = li.create_xsrf_token()
        database.render_template(self, '/users/register_user.html', {'new_li': li, 'xsrf_token' : token})
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
        li.first_name = cgi.escape(database.quick_sanitize(self.request.get('first_name')))
        li.last_name = cgi.escape(database.quick_sanitize(self.request.get('last_name')))
        li.nickname = cgi.escape(database.quick_sanitize(self.request.get("nickname")))
        li.private = bool(self.request.get("private"))
        li.external_user = False
        li.is_active = True
        if user.email() == 'hardcodetest1@gmail.com' or user.email() == 'hardcodetest2@gmail.com':
          li.is_admin = True
        else:
          li.is_admin = database.users.is_current_user_admin()
        li.desc = cgi.escape(database.sanitizeHTML(self.request.get('desc')))
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
      li.first_name = cgi.escape(database.quick_sanitize(self.request.get('first_name')))
      li.last_name = cgi.escape(database.quick_sanitize(self.request.get('last_name')))
      li.email = user.email()
      li.nickname = cgi.escape(database.quick_sanitize(self.request.get('nickname')))
      li.private = bool(self.request.get('private'))
      li.desc = cgi.escape(database.sanitizeHTML(self.request.get('desc')))
      li.external_user = False
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
      #delete item_collections
      item_collections = database.db.GqlQuery("SELECT * FROM ItemCollection WHERE created_by_id = :1", user.user_id())
      for i in item_collections:
        database.db.delete(i)
      #delete the li
      li = database.get_current_li()
      database.logging.info("Deleting LoginInformation user_id=%s", li.user_id)
      database.db.delete(li)
      self.redirect(database.users.create_logout_url('/'))
    else:
      self.redirect('/')
      
class SubmitForeignUserFeedback(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    li = database.get_current_li()
    partner = db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
    if user and li and partner and li.verify_xsrf_token(self):
      #grab all their items
      url = partner.base_url + "/webservices/add_user_rating" 
      try:
        final = {'target_user_id': self.request.get('target_user_id'), 'user_name': li.nickname, 'user_id': li.user_id, 
        'rating': int(self.request.get('rating')), 'feedback': 'Rating', 'auth_token': partner.foreign_auth_token}
        database.logging.info(final)
        result = urlfetch.fetch(url=url, method=urlfetch.POST, payload=urllib.urlencode(final), headers={'Content-Type': 'application/x-www-form-urlencoded'})
        
        database.logging.info(result.content);
        item_contents = json.loads(result.content)
      except Exception, e:
        item_contents = None
    self.redirect('/')
      
#target_user_id: STRING
#user_name: STRING
#user_id: STRING
#rating: FLOAT (1-5)
#feedback: STRING
#feedback_id: STRING

      
class UserFeedbackHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      f = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE for_user_id = :1 AND created_by_id = :2", cgi.escape(self.request.get('for_user_id')), user.user_id())
      if f.count() == 0 and cgi.escape(self.request.get('for_user_id')) != user.user_id(): #can only rate a seller once and you can't rate yourself
        user_feedback = database.UserFeedback()
        user_feedback.created_by_id = user.user_id()
        user_feedback.for_user_id = cgi.escape(self.request.get('for_user_id'))
        rating = int(cgi.escape(self.request.get('rating')))
        if(rating < 0):
          rating = 0
        elif(rating > 5):
          rating = 5
        user_feedback.rating = rating
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
      token = database.get_current_li().create_xsrf_token();
      back_url = self.request.referer
      database.render_template(self, '/users/list_user_feedback.html', {'feedback': feedback, 'li': li, 'back_url': back_url, 'xsrf_token' : token })
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
      
class ExportDataHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    li = database.get_current_li()
    if user and li:
      items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id())
      sent_threads = database.db.GqlQuery("SELECT * FROM Thread WHERE created_by_id = :1", user.user_id())
      recv_threads = database.db.GqlQuery("SELECT * FROM Thread WHERE recipient_id = :1", user.user_id())
      template_values = {'items': items, 'sent_threads': sent_threads, 'recv_threads': recv_threads}
      self.response.headers['Content-Type'] = 'text/plain'
      database.render_template(self, "/users/export_data.txt", template_values)
    else:
      self.redirect('/')
      
class ShowUserShop(database.webapp2.RequestHandler):
  def get(self):
    current_li = database.get_current_li();
    if self.request.get('user_id'):
      user_id = cgi.escape(self.request.get('user_id'))
    else:
      user_id = current_li.user_id
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", user_id).get() 
    token = ""
    if current_li:
      token = database.get_current_li().create_xsrf_token();
    can_show = li.private == False or (current_li and li.user_id == current_li.user_id)
    items = db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1 ORDER BY created_at DESC", li.user_id)
    collections = db.GqlQuery("SELECT * FROM ItemCollection WHERE created_by_id = :1 ORDER BY created_at DESC", li.user_id)
    database.render_template(self, '/users/shop.html', { 'li' : li, 'can_show' : can_show, 'items' : items, 'collections': collections, 'xsrf_token' : token })
    
class ExportUserToForeignApp(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    li = database.get_current_li()
    partner = db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
    if user and li and partner and li.verify_xsrf_token(self):
      #grab all their items
      items = db.GqlQuery("SELECT * FROM Item WHERE created_by_id=:1", user.user_id())
      item_array = []
      for i in items:
        item_hash = {'price': i.price, 'rating': i.rating, 'description': i.description, 'seller': {'username': li.nickname, 'id': li.user_id},'title': i.title}
        item_array.append(item_hash)
      #now generate the JSON
      hash = {'email': li.email, 'google_user_id': li.user_id, 'name': li.nickname, 'bio': li.desc, 'items': item_array}
      url = partner.base_url + "/webservices/user_import"
      try:
        final = {'user_data': json.dumps(hash), 'auth_token': partner.foreign_auth_token}
        database.logging.info(final)
        result = urlfetch.fetch(url=url, method=urlfetch.POST, payload=urllib.urlencode(final), headers={'Content-Type': 'application/x-www-form-urlencoded'})
        
        database.logging.info(result.content);
        item_contents = json.loads(result.content)
      except Exception, e:
        item_contents = None
      if item_contents['success']:
        for i in items:
          i.delete()
        li.delete()
      self.redirect('/')
      return
    else:
      self.redirect('/')
    
app = database.webapp2.WSGIApplication([('/users/', MainHandler), ('/users/verify_user/', RegisterHandler), 
('/users/save_user', SaveLIHandler), ('/users/delete_user', DeleteHandler), ('/users/update_user', UpdateLIHandler),
('/users/submit_feedback', UserFeedbackHandler), ('/users/list_user_feedback',ListUserFeedback), ('/users/delete_user_feedback', DeleteUserFeedback),
('/users/export_data', ExportDataHandler), ('/users/shop', ShowUserShop), ('/users/export_user_foreign', ExportUserToForeignApp),
('/users/submit_foreign_user_feedback', SubmitForeignUserFeedback)], debug=True)
