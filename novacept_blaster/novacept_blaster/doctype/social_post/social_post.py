# Copyright (c) 2022, Novacept and contributors
# For license information, please see license.txt

# import frappe
#from frappe.model.document import Document

import datetime

import frappe
from frappe import _
from frappe.model.document import Document

class SocialPost(Document):
	def validate(self):
		if not self.facebook and not self.instagram and not self.linkedin :
			frappe.throw(_("Select atleast one Social Media Platform"))

		if self.scheduled_time:
			current_time = frappe.utils.now_datetime() - datetime.timedelta(seconds = 45)
			scheduled_time = frappe.utils.get_datetime(self.scheduled_time)
			if scheduled_time < current_time:
				frappe.throw(_("Scheduled Time must be a future time"))

	def submit(self):
		if self.scheduled_time:
			self.post_status = "Scheduled"
		super(SocialPost, self).submit()

	def on_cancel(self):
		self.db_set("post_status", "Cancelled")

	@frappe.whitelist()
	def post(self):
		try:
			if self.facebook:
				facebook = frappe.get_doc("Facebook Setting",self.page_name)
				if self.media_type:
					media_url = frappe.utils.get_url() + self.media
					facebook_post = facebook.post(self.text,self.page_name ,self.media_type ,media_url,self.fb_link)
				else:
#					facebook_post = facebook.post(self.text,self.page_name ,self.fb_link)
					facebook_post = facebook.post(self.text,self.page_name,self.media_type,self.media ,self.fb_link)
			if self.instagram:
				media_url = frappe.utils.get_url() + self.media
				instagram = frappe.get_doc("Instagram Setting",self.acc_name)
				instagram_post = instagram.post(self.caption,self.acc_name, media_url,self.media_type)
			if self.linkedin:
				linkedin = frappe.get_doc("LinkedIn Setting",self.link_page_name)
				linkedin_post = linkedin.post(self.linkedin_post, self.title, self.media)
				print(f'\n\n\n\n{linkedin_post.headers["X-RestLi-Id"]}\n\n\n\n')
			self.db_set("post_status", "Posted")

		except Exception as e:
			frappe.throw(_(e))
			self.db_set("post_status", "Error")
			self.log_error("Social posting failed")

def process_scheduled_social_media_posts():
	print('\n\n\n\n\n\n\n PROCESS \n\n\n\n\n\n')
	posts = frappe.get_list(
		"Social Post",
		filters={"post_status": "Scheduled", "docstatus": 1},
		fields=["name", "scheduled_time"],
	)
	start = frappe.utils.now_datetime() - datetime.timedelta(minutes=4)
	end = frappe.utils.now_datetime() + datetime.timedelta(minutes=6)
	for post in posts:
		if post.scheduled_time:
			post_time = frappe.utils.get_datetime(post.scheduled_time)
			if post_time > start and post_time <= end:
				sm_post = frappe.get_doc("Social Post", post.name)
				sm_post.post()
