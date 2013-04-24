#!/usr/bin/env python

import database
import re
from database import cgi
from database import db
import webservices
import urllib
import json
from google.appengine.api import urlfetch

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    token = ""
    if database.get_current_li() and database.get_current_li().is_admin:
      token = database.get_current_li().create_xsrf_token()
      items = database.db.GqlQuery("SELECT * FROM Item")
    else:
      items = database.db.GqlQuery("SELECT * FROM Item WHERE expiration_date >= :1 AND is_active = :2 AND deactivated = :3", database.datetime.date.today(), True, False)
    trusted_partners = database.TrustedPartner.all()
    database.render_template(self, 'items/index.html', {'items': items, 'xsrf_token' : token, "partners" : trusted_partners })

class NewHandler(database.webapp2.RequestHandler):
  def get(self):
    if database.users.get_current_user():
      token = database.get_current_li().create_xsrf_token()
      database.logging.info("li id: " + str(database.get_current_li().key().id()))
      database.render_template(self, 'items/new_item.html', {"xsrf_token" : token})
    else:
      self.redirect('/')
    
class ViewHandler(database.webapp2.RequestHandler):
  def get(self):
    current_li = database.get_current_li()
    item = db.get(db.Key.from_path('Item', int(self.request.get('item_id'))))
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", item.created_by_id).get()
    token = ""
    if database.users.get_current_user():
      token = database.get_current_li().create_xsrf_token()
    feedback = db.GqlQuery("SELECT * FROM ItemFeedback WHERE item_id = :1 ORDER BY created_at DESC", str(item.key().id()))
    buyer = database.get_user(item.highest_bid_id) 
    rating = None
    if current_li:
      f = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE for_user_id = :1 AND created_by_id = :2", li.user_id, current_li.user_id)
      if f.count() > 0:
        rating = int(f.get().rating)
    database.render_template(self, 'items/view_item.html', {'item': item, 'li': li, 'feedback': feedback, 'buyer': buyer, 'rating':rating, 'xsrf_token' : token})
    
class SaveHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().verify_xsrf_token(self):
      item = database.Item()
      item.title = cgi.escape(database.quick_sanitize(self.request.get('title')))
      item.description = cgi.escape(database.sanitizeHTML(self.request.get('description')))
      if (len(item.description) > 40):
        item.summary = item.description[:40].rstrip() + "..."
      else:
        item.summary = item.description
      item.price = float('%.2f' % float(cgi.escape(self.request.get('price'))))
      item.created_by_id = user.user_id()
      item.is_active = True
      item.deactivated = False
      item.bidding_enabled = bool(self.request.get('bidding_enabled'))
      item.sponsored = bool(self.request.get('sponsored'))
      item.is_active = not bool(self.request.get('show_item'))
      if self.request.get('photo'):
        image = database.images.resize(self.request.get('photo'), 512, 512)
        item.image = db.Blob(image)
      item.expiration_date = database.datetime.date.today() + database.datetime.timedelta(weeks=4) #get 4 weeks of posting
      key = item.put()
      item = database.db.get(db.Key.from_path('Item', key.id()))
      webservices.send_new_item_notification(self, item)
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
      if (item.created_by_id == user.user_id()) or (database.get_current_li().is_admin):
        database.logging.info("Deleting item with id %s by user_id %s", item.key().id(), user.user_id())
        database.db.delete(item)
        for f in feedback:
          db.delete(f)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

    
class EditHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li:
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      if item.created_by_id == current_li.user_id:
        token = database.get_current_li().create_xsrf_token()
        database.render_template(self, 'items/edit_item.html', {'item': item, 'xsrf_token' : token})
      else:
        self.redirect('/')
    else:
      self.redirect('/')
      
class UpdateHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li and current_li.verify_xsrf_token(self):
      item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
      if item.created_by_id == current_li.user_id:
        item.title = cgi.escape(database.quick_sanitize(self.request.get('title')))
        item.description = cgi.escape(database.sanitizeHTML(self.request.get('description')))
        item.bidding_enabled = bool(self.request.get('bidding_enabled'))
        if (len(item.description) > 40):
          item.summary = item.description[:40] + "..."
        else:
          item.summary = item.description
        item.price = float('%.2f' % float(cgi.escape(self.request.get('price'))))
        item.is_active = not bool(self.request.get('show_item'))
        item.sponsored = bool(self.request.get('sponsored'))
        if self.request.get('photo'):
          item.image = database.db.Blob(database.images.resize(self.request.get('photo'), 512, 512))
        database.logging.info("Item #%s changed to:\nTitle: %s\nDescription: %s\nPrice: %f", item.key().id(), item.title, item.description, item.price)
        item.put()
        self.redirect('/items/my_items')
    else:
      self.redirect('/')
    
class ShopHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li:
      token = database.get_current_li().create_xsrf_token()
      items = db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1 ORDER BY created_at DESC", user.user_id())
      database.render_template(self, 'items/my_items.html', {'items': items, 'xsrf_token' : token})
    else:
      self.redirect('/')
    
class SearchHandler(database.webapp2.RequestHandler):
  def get(self):
    query = cgi.escape(database.quick_sanitize(self.request.get('query')))
    limit = cgi.escape(database.quick_sanitize(self.request.get('query_limit')))
    search_by = cgi.escape(database.quick_sanitize(self.request.get('query_search_by')))    
    sort_by = {
      "a" : {
        "sort_field" : cgi.escape(database.quick_sanitize(self.request.get('query_sortA'))),
        "order" : cgi.escape(database.quick_sanitize(self.request.get('query_orderA')))
      },
      "b" : {
        "sort_field" : cgi.escape(database.quick_sanitize(self.request.get('query_sortB'))),
        "order" : cgi.escape(database.quick_sanitize(self.request.get('query_orderB')))
      }
    }

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
    trusted_partners = database.TrustedPartner.all()
    database.render_template(self, 'items/search.html', { 'items': results, 'query': query, "partners" : trusted_partners, 'limit' : limit, 'search_by' : search_by, 'sort_by' : sort_by })
    
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
      rating = int(cgi.escape(self.request.get('rating')))
      if(rating < 0):
        rating = 0
      elif(rating > 5):
        rating = 5
      item_feedback.rating = rating
      item_feedback.feedback = cgi.escape(self.request.get('feedback'))
      item_feedback.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class ForeignItemFeedbackHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    li = database.get_current_li()
    if user and li:
      target_item_id = cgi.escape(self.request.get('item_id'))
      user_name = li.nickname
      user_id = li.user_id
      rating = int(cgi.escape(self.request.get('rating')))
      feedback = cgi.escape(self.request.get('feedback'))
      partner = database.db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
      if partner:
        base_url = partner.base_url
        foreign_auth_token = partner.foreign_auth_token
        url = base_url + "/webservices/add_item_rating"
        form_fields = {'target_item_id': str(target_item_id), 'user_name': user_name, 'user_id': user_id, 'rating': rating, 'feedback': feedback, 'auth_token': foreign_auth_token}
        post_params = urllib.urlencode(form_fields)
        try:
          result = urlfetch.fetch(url=url, method=urlfetch.POST, payload=post_params, headers={'Content-Type': 'application/x-www-form-urlencoded'})
          database.logging.info(result + "\n")
          self.redirect(self.request.referer)
          return
        except Exception, e:
          self.redirect('/')
          return
      else:
        self.redirect('/')
        return
# WTF, someone implement this
#target_item_id: STRING
#user_name: STRING
#user_id: STRING
#rating: FLOAT (1-5)
#feedback: STRING
#feedback_id: STRING
      
class DeleteFeedbackHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      item_feedback = db.get(db.Key.from_path('LoginInformation', int(cgi.escape(self.request.get('created_by'))), 'ItemFeedback', int(cgi.escape(self.request.get('feedback_id')))))
      db.delete(item_feedback)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class BidHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li and current_li.verify_xsrf_token(self):
      bid = float(cgi.escape(self.request.get('bid')))
      item_id = int(cgi.escape(self.request.get('item_id')))
      item = db.get(db.Key.from_path('Item', item_id))
      if item.highest_bid:
        if(bid > float(item.highest_bid) and item.bidding_enabled):
          item.highest_bid = '%.2f' % bid
          item.highest_bid_id = user.user_id()
          item.put()
      else:
        item.highest_bid = '%.2f' % bid
        item.highest_bid_id = user.user_id()
        item.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class SoldHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    item = db.get(db.Key.from_path('Item', int(cgi.escape(self.request.get('item_id')))))
    if user and current_li and current_li.verify_xsrf_token(self) and item.created_by_id == user.user_id():
      item.sold = True
      item.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class NewCollectionHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li:
      token = current_li.create_xsrf_token()
      items = db.GqlQuery("SELECT * FROM Item WHERE expiration_date >= :1 AND is_active = :2 AND deactivated = :3", database.datetime.date.today(), True, False)
      bad_code = ",".join(["{id:\""+str(item.key().id())+"\", name: \""+item.title+"\"}" for item in items])
      database.render_template(self, '/items/new_collection.html', {'list': bad_code, 'xsrf_token' : token})
    else:
      self.redirect('/')

class SaveCollectionHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li and current_li.verify_xsrf_token(self):
      collection = database.ItemCollection()
      collection.title = cgi.escape(self.request.get('title'))
      collection.created_by_id = user.user_id()
      items = cgi.escape(self.request.get('items'))
      items = [y for y in [re.sub("[^0-9]", "", x) for x in items.split("||")] if len(y) > 0]
      item_collection = []
      for item in items:
        item_collection.append(int(item))
      collection.items = item_collection
      collection.put()
      self.redirect('/users/shop')
    else:
      self.redirect('/')
  
class ViewCollectionHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    collection = db.get(db.Key.from_path('ItemCollection', int(cgi.escape(self.request.get('collection_id')))))
    if user and current_li and collection.created_by_id == user.user_id():
      if len(collection.get_items()) > 0:
        database.render_template(self, '/items/view_collection.html', {'items': collection.get_items()})
      else:
        db.delete(collection)
        self.redirect(self.request.referer)
    else:
      self.redirect('/')
      
class DeleteCollectionHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    collection = db.get(db.Key.from_path('ItemCollection', int(cgi.escape(self.request.get('collection_id')))))
    if user and current_li and (collection.created_by_id == user.user_id() or current_li.is_admin):
      db.delete(collection)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

class RemoteItemHandler(database.webapp2.RequestHandler):
  def get(self):
    current_li = database.get_current_li()
    item_id = self.request.get("item_id")
    partner_id = cgi.escape(self.request.get('partner_id'))
    partner = database.db.get(db.Key.from_path('TrustedPartner', int(partner_id)))
    item_contents = None
    if partner:
      base_url = partner.base_url
      foreign_auth_token = partner.foreign_auth_token
      url = base_url + "/webservices/item?auth_token=" + foreign_auth_token + "&item_id=" + item_id
      try:
        result = urlfetch.fetch(url=url, method=urlfetch.GET, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        database.logging.info(result.content);
        item_contents = json.loads(result.content)
      except Exception, e:
        item_contents = None
    seller_id = ""
    if item_contents:
      seller_id = str(item_contents["seller"]["id"])

    seller_name = ""
    if item_contents:
      seller_name = str(item_contents["seller"]["username"])

    database.logging.info("item contents: " + json.dumps(item_contents))
    database.render_template(self, '/items/view_remote_item.html', {'item_contents': item_contents, 'partner_id' : partner_id, 'item_id' : str(item_id), 'seller_id' : seller_id, 'seller_name' : seller_name })


app = database.webapp2.WSGIApplication([('/items/', MainHandler), ('/items/new_item', NewHandler), 
('/items/save_item', SaveHandler), ('/items/view_item', ViewHandler), ('/items/search', SearchHandler),
('/items/my_items', ShopHandler), ('/items/delete_item', DeleteHandler), ('/items/edit_item', EditHandler),
('/items/update_item', UpdateHandler), ('/items/submit_feedback', FeedbackHandler), ('/items/delete_item_feedback', DeleteFeedbackHandler),
('/items/old_searches', OldSearches), ('/items/submit_bid', BidHandler), ('/items/item_sold', SoldHandler), ('/items/new_collection', NewCollectionHandler),
('/items/save_collection', SaveCollectionHandler), ('/items/view_collection', ViewCollectionHandler), ('/items/delete_collection', DeleteCollectionHandler), 
('/items/view_remote_item', RemoteItemHandler), ('/items/submit_foreign_feedback', ForeignItemFeedbackHandler)], debug=True)
