#!/usr/bin/env python

import database
import json
from database import db
cgi = database.cgi

def item_to_dictionary(item, self):
	return {
		"id" : item.key().id(),
		"title" : item.title,
		"description" : item.description,
		"image" : self.request.host + item.display_image_url(),
		"seller" : seller_to_dictionary(item.get_creator()),
		"price" : str(item.price),
		"url" : self.request.host + "/items/view_item?item_id=" + str(item.key().id()),
		"created_at" : item.created_at.strftime("%m/%d/%Y"),
		"expiration_date" : item.expiration_date.strftime("%m/%d/%Y")
	}


def seller_to_dictionary(seller):
	return {
		"id" : seller.user_id,
		"username" : seller.get_display_name()
	}

  
class AddItemRatingHandler(database.webapp2.RequestHandler):
  def post(self):
    #fill out the item feedback
    feedback = database.ItemFeedback()
    feedback.created_by_id = cgi.escape(self.request.get('user_id'))
    feedback.item_id = cgi.escape(self.request.get('target_item_id'))
    feedback.rating = int(cgi.escape(self.request.get('rating')))
    feedback.feedback = cgi.escape(self.request.get('feedback'))
    success = False
    err_mess = ""
    try:
      feedback.put()
      success = True
      err_mess = "Saved to datastore successfully."
    except TransactionFailedError:
      success = False
      err_mess = "Could not save to datastore."
    j = json.dumps({"success": success, "message": err_mess, "feedback_id": feedback.key().id()})
    self.response.out.write(j)
    
class AddUserRatingHandler(database.webapp2.RequestHandler):
  def post(self):
    #fill out the user feedback
    feedback = database.UserFeedback()
    feedback.created_by_id = cgi.escape(self.request.get('user_id'))
    feedback.for_user_id = cgi.escape(self.request.get('target_user_id'))
    feedback.rating = int(cgi.escape(self.request.get('rating')))
    success = False
    err_mess = ""
    try:
      feedback.put()
      success = True
      err_mess = "Saved to datastore successfully."
    except TransactionFailedError:
      success = False
      err_mess = "Could not save to datastore."
    j = json.dumps({"success": success, "message": err_mess, "feedback_id": feedback.key().id()})
    self.response.out.write(j)
  
class WebservicesSearchHandler(database.webapp2.RequestHandler):
	def get(self):
		search_by_params = ["title", "description", "price"]
		sort_types = ["title", "description", "price", "time_create", "location"]
		query = cgi.escape(self.request.get("query"))
		limit = cgi.escape(self.request.get("limit"))
		offset = cgi.escape(self.request.get("offset"))
		search_by = cgi.escape(self.request.get("search_by"))
		sort_options = json.loads(self.request.get("sort_options"))

		if len(str(limit)) == 0:
			limit = "10"

		if len(str(offset)) == 0:
			offset = "0"
		
		if not(search_by in search_by_params):
			search_by = "title"

		#Type cast params... they need to be in try catches ugh >.<
		try:
			limit = int(limit)
			if limit <= 0:
				limit = 10
		except ValueError, e:
			limit = 10

		try:
			offset = int(offset)
			if offset < 0:
				offset = 0
		except ValueError, e:
			offset = 0

		directionA = False
		directionB = ""
		sort_typeA = sort_options[0]["type"]
		sort_typeB = sort_options[1]["type"]

		if sort_options[0]["ordering"] == "desc":
			directionA = True

		if sort_options[1]["ordering"] == "desc":
			directionB = "-"

		if not(sort_typeA in sort_types):
			sort_typeA = "title"
		elif sort_typeA == "time_create":
			sort_typeA = "created_at"

		if not(sort_typeB in sort_types):
			sort_typeB = "title"
		elif sort_typeB == "time_create":
			sort_typeB = "created_at"

		orderB = directionB + sort_typeB

		items = database.Item.all().order(orderB)
		#now tokenize the input by spaces

		query_tokens = database.string.split(query)
		tmp_results = []
		for item in items:
			add = False
			if search_by == "title":
				for tok in query_tokens:
					if database.string.find(item.title, tok) != -1:
						add = True
			elif search_by == "description":
				for tok in query_tokens:
					if database.string.find(item.description, tok) != -1:
						add = True
			elif search_by == "price":
				for tok in query_tokens:
					if database.string.find(str(item.price), tok) != -1:
						add = True
			if add:
				tmp_results.append(item_to_dictionary(item, self))

		database.logging.info("SortA : " + sort_typeA + ", orderB : " + orderB)

		tmp_results = sorted(tmp_results, key=lambda x:x[sort_typeA])
		database.logging.info(json.dumps(tmp_results))

		results = []
		tmp_offset = offset
		counter = 0
		count = 0
		for res in tmp_results:
			if count >= limit:
				break
			tmp_offset -= 1
			counter = counter + 1
			if tmp_offset < 0:
				count = count + 1
				results.append(res)

		b = json.dumps({ "items" : results, "results_left" : len(list(tmp_results)) - counter, "total" : len(list(tmp_results)) })

		database.logging.info("B should be : " + b)

		self.response.out.write(b)


class WebservicesItemHandler(database.webapp2.RequestHandler):
	def get(self):
		auth_token = cgi.escape(self.request.get('auth_token'))
		item_id = cgi.escape(self.request.get('item_id'))
		try:
			item = db.get(db.Key.from_path('Item', int(item_id)))
			self.response.out.write(item_to_dictionary(item))
		except ValueError:
			failure = json.dumps({ "success" : False, "message" : "item_id does not exist"})
			self.response.out.write(failure)
		except AttributeError:
			failure = json.dumps({ "success" : False, "message" : "item_id does not exist"})
			self.response.out.write(failure)

class WebservicesTestHandler(database.webapp2.RequestHandler):
	def get(self):
		self.response.out.write(json.dumps([item_to_dictionary(i) for i in database.Item.all()]))

app = database.webapp2.WSGIApplication([('/webservices/search', WebservicesSearchHandler), ('/webservices/add_user_rating', AddUserRatingHandler), 
('/webservices/add_item_rating', AddItemRatingHandler), ('/webservices/item', WebservicesItemHandler), ('/webservices/test', WebservicesTestHandler)], debug=True)

