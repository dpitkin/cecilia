#!/usr/bin/env python

import database
from database import db
import hashlib
import random
import time

cgi = database.cgi

class MainHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin:
      token = database.get_current_li().create_xsrf_token()
      test_data = database.db.GqlQuery("SELECT * FROM IsTestDataLoaded").get()
      if not test_data:
        test_data = database.IsTestDataLoaded(test_data_loaded=False)
        test_data.put()
      is_test_data_loaded = test_data.is_test_data_loaded
      activated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, True)
      deactivated_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, False)
      database.render_template(self, '/admin/index.html', {'activated_users': activated_users, 'deactivated_users': deactivated_users, 'is_test_data_loaded': is_test_data_loaded, 'xsrf_token' : token })
    else:
      self.redirect('/')

class ActivationHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      user.is_active = not user.is_active
      user.put()
      if not user.is_active:
        items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id)
        for item in items:
          item.deactivated = True
          item.put()
      else:
        items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id)
        for item in items:
          item.deactivated = False
          item.put()
      database.logging.info("ActivationHandler used, user#%s active=%s\n", user.user_id, user.is_active)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

class ModifyHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin:
      token = database.get_current_li().create_xsrf_token()
      registered_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 AND is_active = :2 ORDER BY nickname", False, True)
      admin_users = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE is_admin = :1 ORDER BY nickname", True)
      database.render_template(self, '/admin/modify.html', {'registered_users': registered_users, 'admin_users': admin_users, 'xsrf_token' : token })
    else:
      self.redirect('/')

class CreateAdminHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", cgi.escape(self.request.get('user_id'))).get()
      user.is_admin = True
      user.put()
      database.logging.info("CreateAdminHandler used, user#%s is_admin=%s\n", user.user_id, user.is_admin)
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

class LoadTestDataHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      test_data = database.db.GqlQuery("SELECT * FROM IsTestDataLoaded").get()
      is_test_data_loaded = test_data.is_test_data_loaded 
      if not is_test_data_loaded:
        for i in range(0, 25):
          li = database.LoginInformation(first_name="user",last_name=str(i), user_id="00" + str(i).zfill(2), email="user" + str(i) + "@example.com", is_active=True, is_admin=False, nickname="user" + str(i), private=False)
          li.put()
          database.logging.info("Creating test data user_id=%s", li.user_id)
          for j in range(0, 10):
            item = database.Item(title="item" + str((i * 10) + j), description="This is a description of the item. It may contain various amounts of information.", price=float('%.2f' % float((i * 10) + j)), expiration_date=database.datetime.date.today() + database.datetime.timedelta(weeks=4), is_active=True, deactivated=False, created_by_id=li.user_id)
            if (len(item.description) > 40):
              item.summary = item.description[:40].rstrip() + "..."
            else:
              item.summary = item.description           
            item.put()
      else:
        for i in range(0, 25):
          user = database.db.GqlQuery("SELECT * FROM LoginInformation WHERE user_id = :1", "00" + str(i).zfill(2)).get()
          if user:
            #delete all the items
            items = database.db.GqlQuery("SELECT * FROM Item WHERE created_by_id = :1", user.user_id)
            for item in items:
              database.db.delete(item)
            # delete messages
            messages = database.db.GqlQuery("SELECT * FROM Message WHERE created_by_id = :1", user.user_id)
            for m in messages:
              database.db.delete(m)
            # delete threads
            threads = database.db.GqlQuery("SELECT * FROM Thread WHERE created_by_id = :1", user.user_id)
            for t in threads:
              database.db.delete(t)
            # delete user_feedback
            user_feedback = database.db.GqlQuery("SELECT * FROM UserFeedback WHERE created_by_id = :1", user.user_id)
            for f in user_feedback:
              database.db.delete(f)
            # delete item_feedback
            item_feedback = database.db.GqlQuery("SELECT * FROM ItemFeedback WHERE created_by_id = :1", user.user_id)
            for f in item_feedback:
              database.db.delete(f)
            #delete the li
            database.logging.info("Deleting test data user_id=%s", user.user_id)
            database.db.delete(user)
      test_data.is_test_data_loaded = not test_data.is_test_data_loaded
      test_data.put()
      self.redirect('/admin/')
    else:
      self.redirect('/')

class TrustedPartnersHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin:
      token = database.get_current_li().create_xsrf_token()
      partners = database.db.GqlQuery("SELECT * FROM TrustedPartner")
      database.render_template(self, '/admin/partners.html', {'partners' : partners, 'xsrf_token' : token })
    else:
      self.redirect('/')

class SaveTrustedPartnerHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      name = cgi.escape(database.quick_sanitize(self.request.get('name')))
      url = cgi.escape(database.quick_sanitize(self.request.get('url')))
      foreign_auth_token = cgi.escape(database.quick_sanitize(self.request.get('auth_token')))
      local_auth_token = hashlib.sha1(str(random.random()) + url + str(time.clock())).hexdigest()
      partner = database.TrustedPartner()
      partner.name = name
      partner.base_url = url
      partner.local_auth_token = local_auth_token
      if foreign_auth_token != "":
        partner.foreign_auth_token = foreign_auth_token
      else:
        partner.foreign_auth_token = "-1"
      if url != "" and database.db.GqlQuery("SELECT * FROM TrustedPartner WHERE base_url = :1", url).get() == None:
        partner.put()
      self.redirect(self.request.referer)
    else:
      self.redirect('/')

class DeleteTrustedPartnerHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      partner = database.db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
      if partner:
        database.logging.info("Deleting Trusted Partner: %s", partner.base_url)
        database.db.delete(partner)
      self.redirect(self.request.referer)
    else:
      self.redirect('/') 

class EditTrustedPartnerHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li and current_li.is_admin:
      token = current_li.create_xsrf_token()
      partner = database.db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
      database.render_template(self, '/admin/edit_partner.html', {'partner' : partner, 'xsrf_token' : token})
    else:
      self.redirect('/')

class GenerateLocalAuthTokenHandler(database.webapp2.RequestHandler):
  def get(self):
    user = database.users.get_current_user()
    if user and database.get_current_li() and database.get_current_li().is_admin and database.get_current_li().verify_xsrf_token(self):
      token = cgi.escape(self.request.get('xsrf_token'))
      url = cgi.escape(self.request.get('url'))
      partner = database.db.GqlQuery("SELECT * FROM TrustedPartner WHERE base_url = :1", url).get()
      partner.local_auth_token = hashlib.sha1(str(random.random()) + url + str(time.clock())).hexdigest()
      partner.put()
      self.redirect('/admin/partners')
    else:
      self.redirect('/')

class UpdatePartnerHandler(database.webapp2.RequestHandler):
  def post(self):
    user = database.users.get_current_user()
    current_li = database.get_current_li()
    if user and current_li and current_li.is_admin and current_li.verify_xsrf_token(self):
      partner = database.db.get(db.Key.from_path('TrustedPartner', int(cgi.escape(self.request.get('partner_id')))))
      partner.name = cgi.escape(database.quick_sanitize(self.request.get('name')))
      new_url = cgi.escape(database.quick_sanitize(self.request.get('url')))
      new_foreign_auth_token = cgi.escape(database.quick_sanitize(self.request.get('foreign_auth_token')))
      if new_url != "" and database.db.GqlQuery("SELECT * FROM TrustedPartner WHERE base_url = :1", new_url).get() == None:
        partner.base_url = new_url
      partner.foreign_auth_token = new_foreign_auth_token
      partner.put()
      self.redirect('/admin/partners')
    else:
      self.redirect('/')

app = database.webapp2.WSGIApplication([('/admin/', MainHandler), ('/admin/user_activation', ActivationHandler), ('/admin/modify', ModifyHandler), ('/admin/create_admin', CreateAdminHandler), ('/admin/load_test_data', LoadTestDataHandler), ('/admin/partners', TrustedPartnersHandler), ('/admin/save_partner', SaveTrustedPartnerHandler), ('/admin/delete_partner', DeleteTrustedPartnerHandler), ('/admin/edit_partner', EditTrustedPartnerHandler), ('/admin/generate_local_auth_token', GenerateLocalAuthTokenHandler), ('/admin/update_partner', UpdatePartnerHandler)], debug=True)


