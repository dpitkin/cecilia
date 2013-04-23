#!/usr/bin/env python

import database
import json
from database import db
cgi = database.cgi

def authenticate_user(webservice_params):
	return True

def item_to_dictionary(item):
	return {
		"id" : item.key().id(),
		"title" : item.title,
		"description" : item.description,
		"seller" : seller_to_dictionary(item.get_creator()),
		"image" : item.display_image_url(),
		"price" : item.price,
		"url" : "/items/view_item?item_id=" + str(item.key().id())
	}

def seller_to_dictionary(seller):
	return {
		"id" : seller.user_id,
		"username" : seller.get_display_name()
	}

class WebservicesSearchHandler(database.webapp2.RequestHandler):
	def get(self):
		search_by_params = ["title", "description", "price"]
		query = cgi.escape(self.request.get("query"))
		limit = cgi.escape(self.request.get("limit"))
		offset = cgi.escape(self.request.get("offset"))
		search_by = cgi.escape(self.request.get("search_by"))
		sort_options = self.request.get("sort_options")

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

		items = db.GqlQuery("SELECT * FROM Item ORDER BY created_at DESC")
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

class WebservicesItemHandler(database.webapp2.RequestHandler):
	def get(self):
		auth_token = cgi.escape(self.request.get('auth_token'))
		item_id = cgi.escape(self.request.get('item_id'))
		try:
			item = db.get(db.Key.from_path('Item', int(item_id)))
			self.response.out.write(item_to_dictionary(item))
		except ValueError:
			failure = json.dumps({ "success" : False, "message" : "item_id does not exist"})


app = database.webapp2.WSGIApplication([('/webservices/search', WebservicesSearchHandler), ('/webservices/item', WebservicesItemHandler)], debug=True)


