#!/usr/bin/env python
# Dane was here

import database
from database import cgi
from database import db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    self.response.out.write('Hello user')
    
class RegisterHandler(database.webapp2.RequestHandler):
  def get(self):
    template_values = {
      
    }
    template = database.jinja_environment.get_template('users/register_user.html')
    self.response.out.write(template.render(template_values))
    
class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.User()
    user.first_name=cgi.escape(self.request.get('first_name')) 
    user.last_name=cgi.escape(self.request.get('last_name')) 
    user.login=cgi.escape(self.request.get('login'))
    database.save_user(user, cgi.escape(self.request.get('password')))
    self.redirect('/')
    
class AuthorizeHandler(database.webapp2.RequestHandler):
  def post(self):
    login = cgi.escape(self.request.get('login'))
    user = db.GqlQuery("SELECT * FROM User WHERE login = :1 LIMIT 1", login)
    redirect='/'
    if user:
      for u in user:
        hashed_password = database.hashlib.sha512(cgi.escape(self.request.get('password')+str(u.salt))).hexdigest()
        if u.hashed_password == hashed_password:
          redirect = '/items'
    self.redirect(redirect)
    
  
app = database.webapp2.WSGIApplication([('/users/', MainHandler), ('/users/register_user', RegisterHandler), 
('/users/save_user', SaveHandler), ('/users/authorize', AuthorizeHandler)], debug=True)