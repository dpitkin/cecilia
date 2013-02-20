#!/usr/bin/env python

import database
from database import db

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.users.is_current_user_admin():
      database.get_current_li().create_xsrf_token()
      activated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, True)
      deactivated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, False)
      database.render_template(self, '/admin/index.html', {'activated_users': activated_users, 'deactivated_users': deactivated_users})
    else:
      self.redirect('/')

class ActivationHandler(database.webapp2.RequestHandler):
  def get(self):
    admin = database.users.get_current_user()
    if admin and database.users.is_current_user_admin() and database.get_current_li().verify_xsrf_token(self):
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      user.is_active = not user.is_active
      user.put()
      database.logging.info("ActivationHandler used, user#%s active=%s\n", user.user_id, user.is_active)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

class ModifyHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.users.is_current_user_admin():
      database.get_current_li().create_xsrf_token()
      registered_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, True)
      database.render_template(self, '/admin/modify.html', {'registered_users': registered_users})
    else:
      self.redirect('/')

class CreateAdminHandler(database.webapp2.RequestHandler):
  def get(self):
    admin = database.users.get_current_user()
    if admin and database.users.is_current_user_admin() and database.get_current_li().verify_xsrf_token(self):
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      user.is_admin = True
      user.put()
      database.logging.info("CreateAdminHandler used, user#%s is_admin=%s\n", user.user_id, user.is_admin)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

app = database.webapp2.WSGIApplication([('/admin/', MainHandler), ('/admin/user_activation', ActivationHandler), ('/admin/modify', ModifyHandler), ('/admin/create_admin', CreateAdminHandler)], debug=True)


