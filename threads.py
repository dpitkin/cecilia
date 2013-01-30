#!/usr/bin/env python

import database
import re

cgi = database.cgi
db = database.db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    out_unread_thread = []
    in_unread_thread = []
    push = False
    
    #ew, (n+1) queries
    if user:
      sent_threads = db.GqlQuery("SELECT * FROM Thread WHERE created_by_id = :1 ORDER BY created_at DESC", user.user_id())
      for thread in sent_threads:
        children = db.GqlQuery("SELECT * FROM Message WHERE ANCESTOR is :1", thread.key())
        for child in children:
          if child.recipient_id == user.user_id() and child.read == False:
            push = True
            break
          else:
            push = False
        out_unread_thread.append(True) if push else out_unread_thread.append(False)
      
      push = False
      in_threads = db.GqlQuery("SELECT * FROM Thread WHERE recipient_id = :1 ORDER BY created_at DESC", user.user_id())
      for thread in in_threads:
        children = db.GqlQuery("SELECT * FROM Message WHERE ANCESTOR is :1", thread.key())
        for child in children:
          if child.recipient_id == user.user_id() and child.read == False:
            push = True
            break
          else:
            push = False
        in_unread_thread.append(True) if push else in_unread_thread.append(False)
      
      database.render_template(self, 'threads/index.html', {'sent_threads': sent_threads, 'in_threads': in_threads, 'out_unread_thread': out_unread_thread,
      'in_unread_thread': in_unread_thread})
    else:
      self.redirect('/')
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
      thread = db.get(thread_key)
      children = db.GqlQuery("SELECT * FROM Message WHERE ANCESTOR is :1", thread_key)
      for child in children:
        if child.recipient_id == user.user_id():
          child.read = True
          child.put()
      database.render_template(self, 'threads/view_thread.html', {'thread': thread, 'children': children})
    else:
      self.redirect('/')
    
class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      item = None
      if self.request.get("about"): 
        item = db.get(db.Key.from_path('Item', (int(cgi.escape(self.request.get('about'))))))

      database.render_template(self, 'threads/new_thread.html', {'item': item})
    else:
      self.redirect('/')

class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user:
      if self.request.get("item_id"):
        item_id = int(cgi.escape(self.request.get('item_id')))
        recipients = [db.get(db.Key.from_path('Item', item_id)).created_by_id]
      else:
        recipients = cgi.escape(self.request.get("recipients"))
        #WOAH! Rejects everything but numbers, then maps to integers
        recipients = [y for y in [re.sub("[^0-9]", "", x) for x in recipients.split(",")] if len(y) > 0]
      
      recipients = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id IN :1", recipients)
      recipients = [r for r in recipients if r != user]
      if len(recipients) > 0:
        for recipient in recipients:
          thread = database.Thread(created_by_id=user.user_id())
          thread.title = cgi.escape(self.request.get('title'))
          thread.recipient_id = recipient.user_id
          thread.put()
          message = database.Message(parent=thread)
          message.body = cgi.escape(self.request.get('message'))
          message.created_by_id = thread.created_by_id
          message.recipient_id = thread.recipient_id
          message.read = False
          message.put()
      self.redirect('/threads/')
    else:
      self.redirect('/')

class SaveMessageHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user:
      thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
      thread = db.get(thread_key)
      message = database.Message(parent=thread)
      message.body = cgi.escape(self.request.get('message'))
      message.created_by_id = user.user_id()
      message.recipient_id = thread.recipient_id if user.user_id() == thread.created_by_id else thread.created_by_id
      message.read = False
      message.put()
      self.redirect('/threads/view_thread?thread_id='+self.request.get('thread_id'))    
    else:
      self.redirect('/')
    
app = database.webapp2.WSGIApplication([('/threads/', MainHandler), ('/threads/view_thread', ViewHandler), 
('/threads/new_thread', NewHandler), ('/threads/save_thread', SaveHandler), ('/threads/save_message', SaveMessageHandler)], debug=True)