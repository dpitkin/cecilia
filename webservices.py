#!/usr/bin/env python

import database
import json
from database import db
cgi = database.cgi

def authenticate_filter(fn):
  def inner_function(self):
      
      return fn(self)
	return inner_function
  
  
  
def before_filter(fn):
    def inner_function(self):
        # do stuff before
        return fn(self)
    return inner_function

def item_to_dictionary(item):
	return {
		"id" : item.key().id(),
		"title" : item.title,
		"description" : item.description,
		"seller" : item.get_creator().get_display_name(),
		"image" : item.display_image_url(),
		"price" : item.price,
		"url" : "/items/view_item?item_id=" + str(item.key().id())
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
    
def AddUserRatingHandler(database.webapp2.RequestHandler):
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

		directionA = ""
		directionB = ""

		print [l.description for l in list(db.GqlQuery("SELECT description FROM Item").run(limit=5))]

		if sort_options[0]["ordering"] == "desc":
			directionA = "DESC"
		else:
			directionA = "ASC"

		if sort_options[1]["ordering"] == "desc":
			directionB = "DESC"
		else:
			directionB = "ASC"

		if not(sort_options[0]["type"] in sort_types):
			sort_options[0]["type"] = "title"
		elif sort_options[0]["type"] == "time_create":
			sort_options[0]["type"] = "created_at"

		if not(sort_options[1]["type"] in sort_types):
			sort_options[1]["type"] = "title"
		elif sort_options[1]["type"] == "time_create":
			sort_options[1]["type"] = "created_at"

		orderA = directionA + sort_options[0]["type"]
		orderB = directionB + sort_options[1]["type"]		

		items = db.GqlQuery("SELECT * FROM Item ORDER BY " + sort_options[0]["type"] + " " + directionA)
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
					if database.string.find(item.price, tok) != -1:
						add = True
			if add:
				tmp_results.append(item_to_dictionary(item))

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

		b = json.dumps({ "search_by" : search_by, "items" : results, "sort_options" : sort_options, "results_left" : len(list(tmp_results)) - counter, "total" : len(list(tmp_results)) })
		self.response.out.write(b)

app = database.webapp2.WSGIApplication([('/webservices/search', WebservicesSearchHandler), ('/webservices/add_user_rating', AddUserRatingHandler), 
('/webservices/add_item_rating', AddItemRatingHandler)], debug=True)
