# Copyright (c) 2022, Novacept and contributors
# For license information, please see license.txt

# import frappe
#from frappe.model.document import Document
import frappe
from frappe import _
from frappe.core.doctype.communication.email import make
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today, get_datetime

class EmailCamps(Document):
	def validate(self):
		self.set_date()
		self.trial()
		# checking if email is set for lead. Not checking for contact as email is a mandatory field for contact.
		if self.email_campaign_for == "Lead":
			self.validate_lead()
		self.validate_email_camp_already_exists()
		self.update_status()

	def set_date(self):
		if  frappe.utils.get_datetime(self.start_date) < frappe.utils.now_datetime():
			frappe.throw(_("Scheduled Time must be a future time."))
		# set the end date as start date + max(send after days) in campaign schedule
		send_after_days = []
		campaign = frappe.get_doc("Campaign", self.campaign_name)
		for entry in campaign.get("campaign_schedules"):
			send_after_days.append(entry.send_after_days)
		try:
			self.end_date = add_days(frappe.utils.get_datetime(self.start_date), max(send_after_days))
		except ValueError:
			frappe.throw(
				_("Please set up the Campaign Schedule in the Campaign {0}").format(self.campaign_name)
			)

	def validate_lead(self):
		lead_email_id = frappe.db.get_value("Lead", self.recipient, "email_id")
		if not lead_email_id:
			lead_name = frappe.db.get_value("Lead", self.recipient, "lead_name")
			frappe.throw(_("Please set an email id for the Lead {0}").format(lead_name))

	def trial(self):
		print(self.last_post_time)
		self.last_post_time = frappe.utils.now_datetime()
		print(self.last_post_time)
	def validate_email_camp_already_exists(self):
		email_camp_exists = frappe.db.exists(
			"Email Camps",
			{
				"campaign_name": self.campaign_name,
				"recipient": self.recipient,
				"status": ("in", ["In Progress", "Scheduled"]),
				"name": ("!=", self.name),
			},
		)
		if email_camp_exists:
			frappe.throw(
				_("The Campaign '{0}' already exists for the {1} '{2}'").format(
					self.campaign_name, self.email_campaign_for, self.recipient
				)
			)

	def update_status(self):
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		today_date = getdate(today())
		if start_date > today_date:
			self.status = "Scheduled"
		elif end_date >= today_date:
			self.status = "In Progress"
		elif end_date < today_date:
			self.status = "Completed"

	def update_post_status(self):
		frappe.db.set_value("Email Camps",self.name,"last_post_time",frappe.utils.now_datetime())
		frappe.db.commit()

# called through hooks to send campaign mails to leads
def send_email_to_leads_or_contacts():
	email_campaigns = frappe.get_all(
		"Email Camps", filters={"status": ("not in", ["Unsubscribed", "Completed", "Scheduled"])}
	)
	for camp in email_campaigns:
		email_camp = frappe.get_doc("Email Camps", camp.name)
		last_post = email_camp.get("last_post_time")
		campaign = frappe.get_cached_doc("Campaign", email_camp.campaign_name)
		for entry in campaign.get("campaign_schedules"):
			scheduled_date = add_days(email_camp.get("start_date"), entry.get("send_after_days"))
#			last_post = email_camp.get("last_post_time")
			if last_post < scheduled_date < frappe.utils.now_datetime():
				send_mail(entry, email_camp)
				email_camp.update_post_status()

def send_mail(entry, email_camp):
	recipient_list = []
	if email_camp.email_campaign_for == "Email Group":
		for member in frappe.db.get_list(
			"Email Group Member", filters={"email_group": email_camp.get("recipient")}, fields=["email"]
		):
			recipient_list.append(member["email"])
	else:
		recipient_list.append(
			frappe.db.get_value(
				email_camp.email_campaign_for, email_camp.get("recipient"), "email_id"
			)
		)

	email_template = frappe.get_doc("Email Template", entry.get("email_template"))
	sender = frappe.db.get_value("User", email_camp.get("sender"), "email")
	context = {"doc": frappe.get_doc(email_camp.email_campaign_for, email_camp.recipient)}
	# send mail and link communication to document
	comm = make(
		doctype="Email Camps",
		name=email_camp.name,
		subject=frappe.render_template(email_template.get("subject"), context),
		content=frappe.render_template(email_template.get("response"), context),
		sender=sender,
		recipients=recipient_list,
		communication_medium="Email",
		sent_or_received="Sent",
		send_email=True,
		email_template=email_template.name,
	)
	return comm


# called from hooks on doc_event Email Unsubscribe
def unsubscribe_recipient(unsubscribe, method):
	if unsubscribe.reference_doctype == "Email Camps":
		frappe.db.set_value("Email Camps", unsubscribe.reference_name, "status", "Unsubscribed")


# called through hooks to update email campaign status daily
def set_email_campaign_status():
	email_camps = frappe.get_all("Email Camps", filters={"status": ("!=", "Unsubscribed")})
	for entry in email_camps:
		email_camp = frappe.get_doc("Email Camps", entry.name)
		email_camp.update_status()
