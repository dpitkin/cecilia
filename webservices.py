#!/usr/bin/env python

import database
import json
import urllib
from google.appengine.api import urlfetch
from database import db
cgi = database.cgi


def authenticate(auth_token):
	if database.db.GqlQuery("SELECT * FROM TrustedPartner WHERE local_auth_token = :1", auth_token).count() > 0:
		return True
	else:
		return False

def item_to_dictionary(item, self):
	if item.display_image_url() == '':
		item_url = ''
	else:
		item_url = "https://" + self.request.host + item.display_image_url()
	return {
		"id" : item.key().id(),
		"title" : item.title,
		"description" : item.description,
		"image" : item_url,
		"seller" : seller_to_dictionary(item.get_creator()),
		"price" : str(item.price),
		"url" : "https://" + self.request.host + "/items/view_item?item_id=" + str(item.key().id()),
		"created_at" : item.created_at.strftime("%m/%d/%Y"),
		"expiration_date" : item.expiration_date.strftime("%m/%d/%Y")
	}


def seller_to_dictionary(seller):
	return {
		"id" : seller.user_id,
		"username" : seller.get_display_name()
	}

def render_error(self, message):
  resp = json.dumps({"success" : False, "message" : message})
  self.response.out.write(resp)
  
def render_success(self, message):
  resp = json.dumps({"success" : True, "message" : message})
  self.response.out.write(resp)

def handle_search(self, is_local):
	if not(authenticate(self.request.get('auth_token'))):
		render_error(self, "Invalid auth token.")
		return
	search_by_params = ["title", "description", "price"]
	sort_types = ["title", "description", "price", "time_create", "location"]
	query = cgi.escape(self.request.get("query"))
	limit = cgi.escape(self.request.get("limit"))
	offset = cgi.escape(self.request.get("offset"))
	search_by = cgi.escape(self.request.get("search_by"))
	
	try:
		sort_options = json.loads(self.request.get("sort_options"))
	except Exception, e:
		sort_options = [{"type" : "time_create", "ordering" : "desc"}, {"type" : "time_create", "ordering" : "desc"}]

	if len(str(limit)) == 0:
		render_error(self, "No limit provided")
		return

	if len(str(offset)) == 0:
		render_error(self, "No offset provided")
		return


	#Type cast params... they need to be in try catches ugh >.<
	try:
		limit = int(limit)
		if limit <= 0:
			render_error(self, "Invalid limit parameter: Less than 0")
			return
	except ValueError, e:
		render_error(self, "Invalid limit parameter: Not a number")
		return

	try:
		offset = int(offset)
		if offset < 0:
			render_error(self, "Invalid offset parameter: Less than 0")
			return
	except ValueError, e:
		render_error(self, "Invalid offset parameter: Not a number")

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

	tmp_tokens = database.string.split(query)
	query_tokens = []

	database.logging.info("before")
	if database.db.GqlQuery("SELECT * FROM Suggestion WHERE query = :1", query).get() == None:
		suggestion = database.Suggestion()
		suggestion.query = query
		suggestion.put()
		database.logging.info("suggestion.put() executed")
	database.logging.info("after")

	for tok in tmp_tokens:
		split_val = tok.split(":")
		if len(split_val) == 1:
			query_tokens.append( ("title", split_val[0]) )
		else:
			column = split_val[0]
			if not(column in search_by_params):
				column = "title"
			query_tokens.append( (column, split_val[1]) )

	tmp_results = []

	for item in items:
		add = False
		for tok in query_tokens:
			param = item.title
			if tok[0] == "description":
				param = item.description
			if tok[0] == "price":
				param = str(item.price)
			if database.string.find(param, tok[1]) != -1:
				add = True
		if add:
			tmp_results.append(item_to_dictionary(item, self))
				

	tmp_results = sorted(tmp_results, key=lambda x:x[sort_typeA])

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

	b = json.dumps({ "items" : results, "results_left" : len(list(tmp_results)) - counter, "total" : len(list(tmp_results)), "success" : True })
	self.response.out.write(b)

def send_new_item_notification(self, item):
	partners = database.db.GqlQuery("SELECT * FROM TrustedPartner")
	for partner in partners:
		base_url = partner.base_url
		foreign_auth_token = partner.foreign_auth_token
		url = base_url + "/webservices/new_item"

		j = json.dumps({ "auth_token" : partner.foreign_auth_token, "data" : [item_to_dictionary(item, self)] })
		try:
			result = urlfetch.fetch(url=url, payload=j, method=urlfetch.POST, headers={'Content-Type': 'application/x-www-form-urlencoded'})
			database.logging.info("Partner: " + str(partner.name) + ", Result : " + result.content)
			self.response.out.write(result.content)
		except Exception, e:
			render_error(self, "Something went wrong accessing url, " + e.message)
			database.logging.info("Error : %s", str(e))

class AddItemRatingHandler(database.webapp2.RequestHandler):
  def post(self):
    #fill out the item feedback
    if not(authenticate(self.request.get('auth_token'))):
      render_error(self, "Invalid auth token.")
      return
    external_li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id=:1", cgi.escape(self.request.get('user_id'))).get()
    if not(external_li):
      external_li = database.create_external_user(cgi.escape(self.request.get('user_id')))
    feedback = database.ItemFeedback(parent=external_li)
    feedback.created_by_id = cgi.escape(self.request.get('user_id'))
    feedback.item_id = cgi.escape(self.request.get('target_item_id'))
    feedback.parent = external_li
    feedback.rating = int(float(cgi.escape(self.request.get('rating'))))
    if feedback.rating > 5:
      feedback.rating = 5
    elif feedback.rating < 1:
      feedback.rating = 1
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
    j = json.dumps({"success": success, "message": err_mess, "feedback_id": str(feedback.key().id())})
    self.response.out.write(j)
    
class AddUserRatingHandler(database.webapp2.RequestHandler):
  def post(self):
    if not(authenticate(self.request.get('auth_token'))):
      render_error(self, "Invalid auth token.")
      return
    #fill out the user feedback
    feedback = database.UserFeedback()
    feedback.created_by_id = cgi.escape(self.request.get('user_id'))
    external_li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id=:1", feedback.created_by_id).get()
    if not(external_li):
      database.create_external_user(feedback.created_by_id)
    feedback.for_user_id = cgi.escape(self.request.get('target_user_id'))
    feedback.rating = int(float(cgi.escape(self.request.get('rating'))))
    if feedback.rating > 5:
      feedback.rating = 5
    elif feedback.rating < 1:
      feedback.rating = 1
    success = False
    err_mess = ""
    try:
      feedback.put()
      success = True
      err_mess = "Saved to datastore successfully."
    except TransactionFailedError:
      success = False
      err_mess = "Could not save to datastore."
    j = json.dumps({"success": success, "message": err_mess, "feedback_id": str(feedback.key().id())})
    self.response.out.write(j)
  
class WebservicesSearchHandler(database.webapp2.RequestHandler):
  def get(self):
    handle_search(self, False)

class WebservicesLocalSearchHandler(database.webapp2.RequestHandler):
  def get(self):
    handle_search(self, True)

class WebservicesPartnerSearchHandler(database.webapp2.RequestHandler):
	def get(self):
		query = cgi.escape(self.request.get("query"))
		limit = cgi.escape(self.request.get("limit"))
		offset = cgi.escape(self.request.get("offset"))
		search_by = cgi.escape(self.request.get("search_by"))
		sort_options = cgi.escape(self.request.get("sort_options"))

		partner_id = self.request.get("partner_id")

		partner = database.db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
		if partner:
			base_url = partner.base_url
			foreign_auth_token = partner.foreign_auth_token
			url = base_url + "/webservices/search?auth_token=" + foreign_auth_token + "&query=" + query + "&limit=" + limit + "&offset=" + offset + "&search_by=" + search_by + "&sort_options=" + sort_options
			try:
				result = urlfetch.fetch(url=url, method=urlfetch.GET, headers={'Content-Type': 'application/x-www-form-urlencoded'})
				self.response.out.write(cgi.escape(result.content))
				return
			except Exception, e:
				render_error(self, "Something went wrong accessing url, " + e.message)
				return
		else:
			render_error(self, "Invalid partner id")
			return


class WebservicesItemHandler(database.webapp2.RequestHandler):
	def get(self):
		auth_token = cgi.escape(self.request.get('auth_token'))
		if authenticate(auth_token):
			item_id = cgi.escape(self.request.get('item_id'))
			try:
				item = db.get(db.Key.from_path('Item', int(item_id)))
				self.response.out.write(json.dumps(item_to_dictionary(item, self)))
			except ValueError:
				render_error(self, "item_id does not exist")
			except AttributeError:
				render_error(self, "item_id does not exist")
		else:
			render_error(self, "authentication failure")

class WebservicesNewItemRequestHandler(database.webapp2.RequestHandler):
	def post(self):
		auth_token = cgi.escape(self.request.get('auth_token'))
		if authenticate(auth_token):
			render_success(self, "new item received")
		else:
			render_error(self, "authentication failure")
    
class SendMessageHandler(database.webapp2.RequestHandler):
	def post(self):
		if not(authenticate(self.request.get('auth_token'))):
			render_error(self, "Invalid auth token.")
			return
		#fill out the thread first
		thread = None
		database.logging.info("Destination : " + self.request.get('destination_conversation_id'))
		try:
			if self.request.get('destination_conversation_id'):
				thread = db.get(db.Key.from_path('Thread', int(cgi.escape(self.request.get('destination_conversation_id')))))
		except Exception, e:
			database.logging.info("invalid destination conversation id: " + self.request.get("destination_conversation_id"))

		err_mess = ""
		success = False
		external_li = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id=:1", cgi.escape(self.request.get('source_user_id'))).get()
		if not(external_li):
			database.logging.info("creating new external LI")
			external_li = database.create_external_user(cgi.escape(self.request.get('source_user_id')))
		if thread:
			if thread.created_by_id != external_li.user_id and thread.recipient_id != external_li.user_id:
				j = json.dumps({"success": False, "message": "Don't try and mess with other people's messages!", "conversation_id": "-1"})
				self.response.out.write(j)
				return
		else:
			thread = database.Thread(external_conversation=True)
			if self.request.get('source_conversation_id'):
				thread.external_conversation_id = cgi.escape(self.request.get('source_conversation_id'))
			thread.title = cgi.escape(self.request.get('subject'))
			thread.recipient_id = cgi.escape(self.request.get('destination_user_id'))
			thread.created_by_id = external_li.user_id
	      #need to fill out item details next!!
			thread.put()
	    
	    #now create a new message
		message = database.Message(parent=thread, read=False)
		message.body = cgi.escape(self.request.get('message'))
		message.created_by_id = external_li.user_id
		message.recipient_id = cgi.escape(self.request.get('destination_user_id'))
		try:
			message.put()
			err_mess = "Saved message successfully."
			success = True
		except TransactionFailedError:
			err_mess = "Could not save message."
			success = False
	    
		j = json.dumps({"success": success, "message": err_mess, "conversation_id": str(thread.key().id())})
		self.response.out.write(j)
    
class UserImportHandler(database.webapp2.RequestHandler):
  def post(self):
    #parse json
    database.logging.info(self.request.get('user_data'))
    j = json.loads(self.request.get('user_data'))
    user_id = str(cgi.escape(j['google_user_id']))
    if not(self.request.get('auth_token')):
      render_error(self, "Invalid auth token.")
      return
    #check if this user already exists in our application
    li = db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id=:1", user_id).get()
    if li:
      resp = json.dumps({"success": False, "message": "User already exists in our application."})
      self.response.out.write(resp)
      return
    else:
      #they don't exist in our application, so now let's create them
      li = database.LoginInformation(first_name=cgi.escape(j['name']), last_name=" ", user_id=user_id, is_active=True, is_admin=False, private=False)
      li.email = cgi.escape(j['email'])
      li.nickname = cgi.escape(j['name'])
      li.external_user = False
      try:
        li.put()
      except TransactionFailedError:
        render_error(self, "Could not save LoginInformation to the datastore.")
        return
      #now import all their items
      for i in j['items']:
        item = database.Item(is_active=True, deactivated=False, bidding_enabled=False, sold=False, sponsored=False)
        item.title = cgi.escape(i['title'])
        item.description = cgi.escape(i['description'])
        item.price = float(i['price'])
        item.expiration_date = database.datetime.date.today() + database.datetime.timedelta(weeks=4)
        item.created_by_id = li.user_id
        if (len(item.description) > 40):
          item.summary = item.description[:40].rstrip() + "..."
        else:
          item.summary = item.description
        try:
          item.put()
        except TransactionFailedError:
          render_error(self, "Could not save item to the datastore.")
          return
      
      #we've now created the user and imported all of their items, so now lets write a success response
      render_success(self, "User successfully imported.")
      return

class WebservicesSearchSuggestionsHandler(database.webapp2.RequestHandler):
	def get(self):
		auth_token = cgi.escape(self.request.get('auth_token'))
		query = cgi.escape(self.request.get('query'))
		if authenticate(auth_token):
			suggestions = database.db.GqlQuery("SELECT * FROM Suggestion WHERE query >= :1 AND query < :2 LIMIT 10", query, unicode(query) + u"\ufffd")
			j = json.dumps({ "success" : True, "message" : "Here are the search suggestions", "items" : [{"fullString" : s.query} for s in suggestions] })
			self.response.out.write(j)		
		else:
			render_error(self, "authentication failure")

class WebservicesLocalSearchSuggestionsHandler(database.webapp2.RequestHandler):
	def get(self):
		query = cgi.escape(self.request.get('query'))
		suggestions = database.db.GqlQuery("SELECT * FROM Suggestion WHERE query >= :1 LIMIT 5", query)
		partners = database.db.GqlQuery("SELECT * FROM TrustedPartner")
		results = [{"name" : "Local Results", "items" : [{"fullString" : s.query} for s in suggestions]}]
		for partner in partners:
			base_url = partner.base_url
			foreign_auth_token = partner.foreign_auth_token
			url = base_url + "/webservices/search_suggestions?auth_token=" + foreign_auth_token + "&query=" + str(query)
			try:
				database.logging.info("A")
				result = urlfetch.fetch(url=url, method=urlfetch.GET, headers={'Content-Type': 'application/x-www-form-urlencoded'})
				result_json = json.loads(result.content)

				database.logging.info("C, " + result.content)				
				results.append({"name" : partner.name, "items" : result_json["items"]})
				database.logging.info("D")				
			except Exception, e:
				database.logging.info("Error : %s", str(e))

		j = json.dumps({ "success" : True, "message" : "Here are the search suggestions", "items" : results })
		self.response.out.write(cgi.escape(j))	
		for s in suggestions:
			database.logging.info("suggestion = %s", str(s.query))
		database.logging.info("done")

app = database.webapp2.WSGIApplication([('/webservices/search', WebservicesSearchHandler), ('/webservices/local_search', WebservicesLocalSearchHandler), 
('/webservices/partner_search', WebservicesPartnerSearchHandler), ('/webservices/add_user_rating', AddUserRatingHandler), ('/webservices/add_item_rating', AddItemRatingHandler), 
('/webservices/item', WebservicesItemHandler), ('/webservices/new_item', WebservicesNewItemRequestHandler), ('/webservices/send_message', SendMessageHandler),
 ('/webservices/user_import', UserImportHandler), ('/webservices/search_suggestions', WebservicesSearchSuggestionsHandler), ('/webservices/local_search_suggestions', WebservicesLocalSearchSuggestionsHandler)], debug=True)


