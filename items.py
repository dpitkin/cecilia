#!/usr/bin/env python

import database
from database import cgi
from database import db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    items = db.GqlQuery("SELECT * FROM Item ORDER BY created_at DESC")
    is_admin = database.users.is_current_user_admin()
    database.render_template(self, 'items/index.html', {'items': items})

class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    if database.users.get_current_user():
      database.get_current_li().create_xsrf_token()
      database.render_template(self, 'items/new_item.html', {})
    else:
      self.redirect('/')
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", item.created_by_id).get()
    if database.users.get_current_user():
      database.get_current_li().create_xsrf_token()
    feedback = db.GqlQuery("SELECT * FROM ItemFeedback WHERE item_id = :1 ORDER BY created_at DESC", str(item.key().id()))
    database.render_template(self, 'items/view_item.html', {'item': item, 'li': li, 'feedback': feedback})
    
class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item = database.Item()
      item.title = cgi.escape(self.request.get('title'))
      item.description = cgi.escape(self.request.get('description'))
      if (len(item.description) > 40):
        item.summary = item.description[:40] + "..."
      else:
        item.summary = item.description
      item.price = '%.2f' % float(cgi.escape(self.request.get('price')))
      item.created_by_id = user.user_id()
      item.is_active = True
      if self.request.get('photo'):
        image = database.images.resize(self.request.get('photo'), 512, 512)
        item.image = db.Blob(image)
      item.expiration_date = database.datetime.date.today() + database.datetime.timedelta(weeks=4) #get 4 weeks of posting
      item.put()
      database.logging.info("Created a new item.\nTitle: %s\nDescription: %s\nPrice: %s\nCreatedBy: %s", item.title, item.description, item.price, item.created_by_id)
      self.redirect('/items/')
    else:
      self.redirect('/')
    
class DeleteHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      feedback = db.GqlQuery("SELECT * FROM ItemFeedback WHERE item_id = :1", str(item.key().id()))
      #make sure the person owns this item or they're an admin
      if (item.created_by_id == user.user_id()) or (database.users.is_current_user_admin()):
        database.logging.info("Deleting item with id %s by user_id %s", item.key().id(), user.user_id())
        database.db.delete(item)
        for f in feedback:
          db.delete(f)
    self.redirect(self.request.referer)
    
class EditHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      database.get_current_li().create_xsrf_token()
      database.render_template(self, 'items/edit_item.html', {'item': item})
    else:
      self.redirect('/')
      
class UpdateHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      item.title = cgi.escape(self.request.get('title'))
      item.description = cgi.escape(self.request.get('description'))
      if (len(item.description) > 40):
        item.summary = item.description[:40] + "..."
      else:
        item.summary = item.description
      item.price = '%.2f' % float(cgi.escape(self.request.get('price')))
      item.is_active = bool(self.request.get('show_item'))
      if self.request.get('photo'):
        item.image = database.db.Blob(database.images.resize(self.request.get('photo')))
      database.logging.info("Item #%s changed to:\nTitle: %s\nDescription: %s\nPrice: %s", item.key().id(), item.title, item.description, item.price)
      item.put()
      self.redirect('/items/my_items')
    else:
      self.redirect('/')
    
class ShopHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      database.get_current_li().create_xsrf_token()
      items = db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1 ORDER BY created_at DESC", user.user_id())
      database.render_template(self, 'items/my_items.html', {'items': items})
    else:
      self.redirect('/')
    
class SearchHandler(database.webapp2.RequestHandler):
  def get(self):
    query = cgi.escape(self.request.get('query'))
    items = db.GqlQuery("SELECT * FROM Item ORDER BY created_at DESC") #grab all the items first
    #now tokenize the input by spaces
    query_tokens = database.string.split(query)
    results = []
    for item in items:
      add = False
      for tok in query_tokens:
        if database.string.find(item.title, tok) != -1:
          add = True
      if add:
        results.append(item)
    user = database.users.get_current_user()
    if user:
      searches = db.GqlQuery("SELECT * FROM Search WHERE created_by_id = :1 AND search = :2", user.user_id(), query)
      if searches.count() == 0:
        search = database.Search()
        search.created_by_id = user.user_id()
        search.search = query
        search.put()
      
    database.render_template(self, 'items/search.html', { 'items': results, 'query': query})
    
class OldSearches(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      searches = db.GqlQuery("SELECT * FROM Search WHERE created_by_id = :1", user.user_id())
      database.render_template(self, 'items/old_searches.html', {'searches': searches})
    else:
      self.redirect('/')
    
class FeedbackHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item_feedback = database.ItemFeedback(parent=database.get_current_li())
      item_feedback.created_by_id = user.user_id()
      item_feedback.item_id = cgi.escape(self.request.get('item_id'))
      item_feedback.rating = int(cgi.escape(self.request.get('rating')))
      item_feedback.feedback = cgi.escape(self.request.get('feedback'))
      item_feedback.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class DeleteFeedbackHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.users.is_current_user_admin() and database.get_current_li().verify_xsrf_token(self):
      item_feedback = db.get(db.Key.from_path('LoginInformation', int(cgi.escape(self.request.get('created_by'))), 'ItemFeedback', int(cgi.escape(self.request.get('feedback_id')))))
      db.delete(item_feedback)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
    

app = database.webapp2.WSGIApplication([('/items/', MainHandler), ('/items/new_item', NewHandler), 
('/items/save_item', SaveHandler), ('/items/view_item', ViewHandler), ('/items/search', SearchHandler),
('/items/my_items', ShopHandler), ('/items/delete_item', DeleteHandler), ('/items/edit_item', EditHandler),
('/items/update_item', UpdateHandler), ('/items/submit_feedback', FeedbackHandler), ('/items/delete_item_feedback', DeleteFeedbackHandler),
('/items/old_searches', OldSearches)], debug=True)