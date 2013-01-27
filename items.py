#!/usr/bin/env python

import database
from database import cgi
from database import db

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    items = db.GqlQuery("SELECT * FROM Item ORDER BY created_at DESC")
    template_values = {'items': items}
    template = database.jinja_environment.get_template('items/index.html')
    self.response.out.write(template.render(template_values))

class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    template_values = {}
    template = database.jinja_environment.get_template('items/new_item.html')
    self.response.out.write(template.render(template_values))
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
    template_values = {'item': item}
    template = database.jinja_environment.get_template('items/view_item.html')
    self.response.out.write(template.render(template_values))
    
class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    item = database.Item()
    item.title = cgi.escape(self.request.get('title'))
    item.description = cgi.escape(self.request.get('description'))
    item.price = '%.2f' % float(cgi.escape(self.request.get('price')))
    item.created_by_id = user.user_id()
    item.put()
    self.redirect('/items/')
    
class SearchHandler(database.webapp2.RequestHandler):
  def post(self):
    query = cgi.escape(self.request.get('query'))
    items = db.GqlQuery("SELECT * FROM Item WHERE title = :1 ORDER BY created_at DESC", query)
    template_values = { 'items': items, 'query': query}
    template = database.jinja_environment.get_template('items/search.html')
    self.response.out.write(template.render(template_values))
    

app = database.webapp2.WSGIApplication([('/items/', MainHandler), ('/items/new_item', NewHandler), 
('/items/save_item', SaveHandler), ('/items/view_item', ViewHandler), ('/items/search', SearchHandler)], debug=True)