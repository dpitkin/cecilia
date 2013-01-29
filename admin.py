#!/usr/bin/env python

import database

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    activated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY first_name", False, True)
    deactivated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY first_name", False, False)
    database.render_template(self, '/admin/index.html', {'activated_users': activated_users, 'deactivated_users': deactivated_users})

class DeactivateHandler(database.webapp2.RequestHandler):
  def post(self):
    admin = database.users.get_current_user()
    if admin and database.users.is_current_user_admin():
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      user.is_active = False
      user.put()
      self.redirect('/admin/')
    else:
      self.redirect('/')

class ReactivateHandler(database.webapp2.RequestHandler):
  def post(self):
    admin = database.users.get_current_user()
    if admin and database.users.is_current_user_admin():
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()  
      user.is_active = True
      user.put()
      self.redirect('/admin/')
    else:
      self.redirect('/')

app = database.webapp2.WSGIApplication([('/admin/', MainHandler), ('/admin/deactivate_user', DeactivateHandler), ('/admin/reactivate_user', ReactivateHandler)], debug=True)