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
      database.render_template(self, 'items/new_item.html', {})
    else:
      self.redirect('/')
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", item.created_by_id).get()
    database.render_template(self, 'items/view_item.html', {'item': item, 'li': li})
    
class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user:
      item = database.Item()
      item.title = cgi.escape(self.request.get('title'))
      item.description = cgi.escape(self.request.get('description'))
      item.price = '%.2f' % float(cgi.escape(self.request.get('price')))
      item.created_by_id = user.user_id()
      item.put()
      database.logging.info("Created a new item.\nTitle: %s\nDescription: %s\nPrice: %s\nCreatedBy: %s", item.title, item.description, item.price, item.created_by_id)
      self.redirect('/items/')
    else:
      self.redirect('/')
    
class DeleteHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
      #make sure the person owns this item or they're an admin
      if (item.created_by_id == user.user_id()) or (database.users.is_current_user_admin()):
        database.logging.info("Deleting item with id %s", item.key().id())
        database.db.delete(item)
    self.redirect(self.request.referer)
    
class EditHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
      database.render_template(self, 'items/edit_item.html', {'item': item})
    else:
      self.redirect('/')
      
class UpdateHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user:
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      item.title = cgi.escape(self.request.get('title'))
      item.description = cgi.escape(self.request.get('description'))
      item.price = cgi.escape(self.request.get('price'))
      database.logging.info("Item #%s changed to:\nTitle: %s\nDescription: %s\nPrice: %s", item.key().id(), item.title, item.description, item.price)
      item.put()
      self.redirect('/items/my_items')
    else:
      self.redirect('/')
    
class ShopHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user:
      items = db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1 ORDER BY created_at DESC", user.user_id())
      database.render_template(self, 'items/my_items.html', {'items': items})
    else:
      self.redirect('/')
    
class SearchHandler(database.webapp2.RequestHandler):
  def post(self):
    query = cgi.escape(self.request.get('query'))
    items = db.GqlQuery("SELECT * FROM Item WHERE title = :1 ORDER BY created_at DESC", query)
    database.render_template(self, 'items/search.html', { 'items': items, 'query': query})
    

app = database.webapp2.WSGIApplication([('/items/', MainHandler), ('/items/new_item', NewHandler), 
('/items/save_item', SaveHandler), ('/items/view_item', ViewHandler), ('/items/search', SearchHandler),
('/items/my_items', ShopHandler), ('/items/delete_item', DeleteHandler), ('/items/edit_item', EditHandler),
('/items/update_item', UpdateHandler)], debug=True)