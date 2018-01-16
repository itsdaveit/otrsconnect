# -*- coding: utf-8 -*-
# Copyright (c) 2018, itsdave GmbH and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.database import Database
import htmllib
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


class OTRSConnectFunctions(Document):


    def unescape(self, s):
        p = htmllib.HTMLParser(None)
        p.save_bgn()
        p.feed(s)
        return p.save_end()

    def get_closed_tickets_dict(self):
        settings = frappe.get_doc("OTRSConnect Settings")
        otrsdb = frappe.database.Database(host=settings.otrs_host, user=settings.db_user, password=settings.db_password)
        otrsdb.begin()
        otrsdb.use(settings.db_name)
        sql = ("SELECT DISTINCT ticket.id, ticket.tn, ticket.title, "
                "ticket.queue_id, ticket.user_id, ticket.responsible_user_id, "
                "ticket.ticket_priority_id, ticket.customer_id, ticket.customer_user_id, "
                "ticket.ticket_state_id, ticket.create_time, ticket.create_by, "
                "ticket.change_time, ticket.change_by "
                "FROM ticket "
                "LEFT JOIN users ON ticket.user_id=users.id "
                "LEFT JOIN customer_company ON customer_company.customer_id=ticket.customer_id "
                "LEFT JOIN time_accounting ON time_accounting.ticket_id=ticket.id "
                "WHERE ticket_state_id = '2' "
                "AND time_accounting.time_unit > 0 "
                ";")
        return otrsdb.sql(sql, as_dict=1)

    def set_ERPNext_OTRS_Tickets(self, closed_tickets_dict):
        for ticket in closed_tickets_dict:
            ERPNext_tickets = frappe.get_all("OTRSConnect Ticket", filters={"id": ticket["id"]})
            if len(ERPNext_tickets) == 0:
                frappe_doctype_dict = {"doctype": "OTRSConnect Ticket"}
                ticket["id"] = str(ticket["id"])
                frappe_doctype_dict.update(ticket)
                ticket_doc = frappe.get_doc(frappe_doctype_dict)
                inserted_ticket_doc = ticket_doc.insert()
                self.link_ERPNext_OTRS_Ticket(inserted_ticket_doc)
                self.set_ERPNext_OTRS_Articles(self.get_Articles_for_Ticket_dict(inserted_ticket_doc))

            else:
                frappe.msgprint("Ticket " + str(ticket["id"]) + " bereits vorhanden")


    def link_ERPNext_OTRS_Tickets(self, OTRSConnect_Tickets_dict):
        pass


    def link_ERPNext_OTRS_Ticket(self, OTRSConnect_Ticket):
            naming_series = "CUST-" + OTRSConnect_Ticket.customer_id
            customers_for_customer_id = frappe.get_all("Customer", filters={"naming_series": naming_series})
            if len(customers_for_customer_id) == 1:
                OTRSConnect_Ticket.erpnext_customer = naming_series
                OTRSConnect_Ticket.save()
            else:
                frappe.msgprint("Kundennummerzuweisung nicht eindeutig möglich für: " + OTRSConnect_Ticket.customer_id )

    def get_Articles_for_Ticket_dict(self, OTRSConnect_Ticket):
        settings = frappe.get_doc("OTRSConnect Settings")
        otrsdb = frappe.database.Database(host=settings.otrs_host, user=settings.db_user, password=settings.db_password)
        otrsdb.begin()
        otrsdb.use(settings.db_name)
        sql = ("SELECT article.id, article.ticket_id, article.create_time, "
                "article.create_by, article_data_mime.a_from, article_data_mime.a_to, "
                "article_data_mime.a_subject, article_data_mime.a_body, "
                "time_accounting.time_unit "
                "FROM article "
                "LEFT JOIN article_data_mime ON article.id=article_data_mime.id "
                "LEFT JOIN time_accounting time_accounting ON article.id=time_accounting.article_id "
                "WHERE time_accounting.time_unit > 0 "
                "AND article.ticket_id = " + str(OTRSConnect_Ticket.id) + "; ")
        return otrsdb.sql(sql, as_dict=1)



    def set_ERPNext_OTRS_Articles(self, OTRSConnect_Articles_dict):
        for article in OTRSConnect_Articles_dict:
            ERPNext_articles = frappe.get_all("OTRSConnect Article", filters={"id": article["id"]})
            if len(ERPNext_articles) == 0:
                frappe_doctype_dict = {"doctype": "OTRSConnect Article"}
                article["id"] = str(article["id"])
                article["ticket_id"] = str(article["ticket_id"])
                #article["a_from"] = self.unescape(article["a_from"])
                #article["a_to"] = self.unescape(article["a_to"])
                #article["a_body"] = self.unescape(article["a_body"])
                frappe_doctype_dict.update(article)
                print frappe_doctype_dict
                article_doc = frappe.get_doc(frappe_doctype_dict)
                inserted_article_doc = article_doc.insert()
                #self.link_ERPNext_OTRS_Ticket(inserted_ticket_doc)
                #self.set_ERPNext_OTRS_Articles(self.get_Articles_for_Ticket_dict(inserted_ticket_doc))

            else:
                frappe.msgprint("Artikel " + article["id"] + " bereits vorhanden")
        pass








    def fetch_tickets(self):
        closed_tickets_dict = self.get_closed_tickets_dict()
        if len(closed_tickets_dict) >= 1:
            self.set_ERPNext_OTRS_Tickets(closed_tickets_dict)
