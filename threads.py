#!/usr/bin/env python

import database
import re
import urllib
from google.appengine.api import urlfetch

cgi = database.cgi
db = database.db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    out_unread_thread = []
    in_unread_thread = []
    push = False
    
    #ew, (n+1) queries
    if database.get_current_li():
      token = database.get_current_li().create_xsrf_token()
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
      'in_unread_thread': in_unread_thread, 'xsrf_token': token})
    else:
      self.redirect('/')
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      token = database.get_current_li().create_xsrf_token()
      thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
      thread = db.get(thread_key)
      if thread.recipient_id == user.user_id() or thread.created_by_id == user.user_id():
        children = db.GqlQuery("SELECT * FROM Message WHERE ANCESTOR is :1", thread_key)
        for child in children:
          if child.recipient_id == user.user_id():
            child.read = True
            child.put()
        database.render_template(self, 'threads/view_thread.html', {'thread': thread, 'children': children, 'xsrf_token' : token})
      else:
        self.redirect('/')
    else:
      self.redirect('/')
    
class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      lis = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id != :1", user.user_id())
      token = database.get_current_li().create_xsrf_token()
      item = None
      if self.request.get("about"): 
        item = db.get(db.Key.from_path('Item', (int(cgi.escape(self.request.get('about'))))))
      
      bad_code = ",".join(["{id:\""+str(li.user_id)+"\", name: \""+li.get_display_name()+"\"}" for li in lis if li.get_display_name()])
      database.render_template(self, 'threads/new_thread.html', {'item': item, 'lis': lis, 'list':bad_code, 'xsrf_token' : token})
    else:
      self.redirect('/')

class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item = None
      if self.request.get("item_id"):
        item_id = int(cgi.escape(self.request.get('item_id')))
        item = db.get(db.Key.from_path('Item', item_id))
        recipients = [item.created_by_id]
      else:
        recipients = cgi.escape(self.request.get("recipients"))
        #WOAH! Rejects everything but numbers, then maps to integers
        recipients = [y for y in [re.sub("[^0-9]", "", x) for x in recipients.split("||")] if len(y) > 0]
      recipients = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id IN :1", recipients)
      recipients = [r for r in recipients if r != user]
      if len(recipients) > 0:
        for recipient in recipients:
          database.logging.info("HERE");
          thread = database.Thread(created_by_id=user.user_id())
          if item:
            thread.item_details = 'This is about your item: "' + item.title + '" that you posted for $' + str(item.price)
          thread.title = cgi.escape(self.request.get('title'))
          thread.external_conversation = False
          thread.recipient_id = recipient.user_id
          thread.put()
          database.logging.info("Created a new thread. Info:\nThreadID: %s\nCreatedBy: %s\nTitle: %s\nSentTo: %s\nCreatedAt: %s", 
          thread.key().id(), thread.created_by_id, thread.title, thread.recipient_id, thread.created_at)
          message = database.Message(parent=thread)
          message.body = cgi.escape(self.request.get('message'))
          message.created_by_id = thread.created_by_id
          message.recipient_id = thread.recipient_id
          message.read = False
          message.put()
          database.logging.info("Created a new message under thread #%s\nSentBy: %s\nSentTo: %s\nCreatedAt: %s",
          message.parent().key().id(), message.created_by_id, message.recipient_id, message.created_at)
      self.redirect('/threads/')
    else:
      self.redirect('/')

class SaveMessageHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    thread_key = db.Key.from_path('Thread', int(self.request.get('thread_id')))
    thread = db.get(thread_key)
    if user and database.get_current_li().verify_xsrf_token(self) and (thread.recipient_id == user.user_id() or thread.created_by_id == user.user_id()):
      if thread.external_conversation:
        #its an external conversation, so we should send the message out to the other users API
        None
        #Request:
        #auth_token: STRING
        #item_id: STRING
        #source_user_id: STRING
        #source_user_name: STRING
        #destination_user_id: STRING
        #subject: STRING
        #message: STRING
        #source_conversation_id: STRING
        #destination_conversation_id: STRING

        #result = urlfetch.fetch(url=url, method=urlfetch.GET, headers={'Content-Type': 'application/x-www-form-urlencoded'})
				#self.response.out.write(result.content)
      else:
        message = database.Message(parent=thread)
        message.body = cgi.escape(self.request.get('message'))
        message.created_by_id = user.user_id()
        message.recipient_id = thread.recipient_id if user.user_id() == thread.created_by_id else thread.created_by_id
        message.read = False
        message.put()
        database.logging.info("Created a new message under thread #%s\nSentBy: %s\nSentTo: %s\nCreatedAt: %s",
        message.parent().key().id(), message.created_by_id, message.recipient_id, message.created_at)
      self.redirect('/threads/view_thread?thread_id='+self.request.get('thread_id'))
      return
    else:
      self.redirect('/')
    
app = database.webapp2.WSGIApplication([('/threads/', MainHandler), ('/threads/view_thread', ViewHandler), 
('/threads/new_thread', NewHandler), ('/threads/save_thread', SaveHandler), ('/threads/save_message', SaveMessageHandler)], debug=True)