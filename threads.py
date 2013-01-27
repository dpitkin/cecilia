#!/usr/bin/env python

import database

cgi = database.cgi
db = database.db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    threads = db.GqlQuery("SELECT * FROM Thread ORDER BY created_at DESC")
    template_values = {'threads': threads}
    template = database.jinja_environment.get_template('threads/index.html')
    self.response.out.write(template.render(template_values))
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
    thread = db.get(thread_key)
    children = db.GqlQuery("SELECT * FROM Message WHERE ANCESTOR is :1", thread_key)
    template_values = {'thread': thread, 'children': children}
    template = database.jinja_environment.get_template('threads/view_thread.html')
    self.response.out.write(template.render(template_values))
    
class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    template_values = {}
    template = database.jinja_environment.get_template('threads/new_thread.html')
    self.response.out.write(template.render(template_values))  

class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    thread = database.Thread(created_by_id=user.user_id())
    thread.title = cgi.escape(self.request.get('title'))
    thread.put()
    message = database.Message(parent=thread)
    message.body = cgi.escape(self.request.get('message'))
    message.put()
    self.redirect('/threads/')  

class SaveMessageHandler(database.webapp2.RequestHandler):
  def post(self):
    thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
    thread = db.get(thread_key)
    message = database.Message(parent=thread)
    message.body = cgi.escape(self.request.get('message'))
    message.put()
    self.redirect('/threads/view_thread?thread_id='+self.request.get('thread_id'))     
  
app = database.webapp2.WSGIApplication([('/threads/', MainHandler), ('/threads/view_thread', ViewHandler), 
('/threads/new_thread', NewHandler), ('/threads/save_thread', SaveHandler), ('/threads/save_message', SaveMessageHandler)], debug=True)