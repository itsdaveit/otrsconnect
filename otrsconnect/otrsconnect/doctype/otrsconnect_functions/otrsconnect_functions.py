# -*- coding: utf-8 -*-
# Copyright (c) 2018, itsdave GmbH and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.database import get_db
from time import sleep
#import htmllib
import sys
#reload(sys)
#sys.setdefaultencoding('utf-8')


class OTRSConnectFunctions(Document):

    def test_db_connection(self):
        settings = frappe.get_doc("OTRSConnect Settings")
        otrsdb = get_db(host=settings.otrs_host, user=settings.db_user, password=settings.db_password)
        print(settings.otrs_host)
        print(settings.db_user)
        print(settings.db_password)
        otrsdb.connect()
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
        result = otrsdb.sql(sql, as_dict=1)
        frappe.msgprint(str(len(result)) + " Tickets gefunden")


    def get_closed_tickets_dict(self):
        settings = frappe.get_doc("OTRSConnect Settings")
        print(settings.otrs_host)
        print(settings.db_user)
        print(settings.db_password)

        otrsdb = get_db(host=settings.otrs_host, user=settings.db_user, password=settings.db_password)
        otrsdb.connect()
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
        run_count = 0
        for ticket in closed_tickets_dict:
            run_count += 1
            percent = run_count * 100 / len(closed_tickets_dict)
            frappe.publish_progress(percent, "verarbeite Tickets")
            ERPNext_tickets = frappe.get_all("OTRSConnect Ticket", filters={"id": ticket["id"]})
            if len(ERPNext_tickets) == 0:
                frappe_doctype_dict = {"doctype": "OTRSConnect Ticket"}
                ticket["id"] = str(ticket["id"])
                ticket["status"] = "fetched"
                frappe_doctype_dict.update(ticket)
                ticket_doc = frappe.get_doc(frappe_doctype_dict)
                inserted_ticket_doc = ticket_doc.insert()
                self.link_ERPNext_OTRS_Ticket(inserted_ticket_doc)
                self.set_ERPNext_OTRS_Articles(self.get_Articles_for_Ticket_dict(inserted_ticket_doc))
        frappe.msgprint(str(run_count) + " Tickets verarbeitet.")

    def parse_article_body(self, article_a_body):
        description = ""
        lines = article_a_body.splitlines()
        for line in lines:
            if line.startswith("#"):
                line = "-" + line[1:]
                description = description + str(line + "<br>")
        return description


    def get_items_for_delivery_note_from_articles(self, ticket):
        articles = frappe.get_all("OTRSConnect Article", filters={"ticket_id": ticket.name})
        delivery_note_itmes_list = []
        for article_name in articles:
            article = frappe.get_doc("OTRSConnect Article", article_name.name)
            user = frappe.get_doc("OTRSConnect User", str(article.create_by))
            employee_name = frappe.get_doc("Employee", user.erpnext_employee).employee_name
            description = self.parse_article_body(article.a_body)
            #Check whether remote (rs) or On-Site (os) service
            item = user.erpnext_os_item
            try:
                description_lines = description.splitlines()[0]
            except IndexError:
                frappe.throw("Fehler in OTRS Article " + article_name.name + " aus OTRS Ticket " + ticket.name + "<br>" +
                            "Keine Arbeitsposition mit # erfasst, aber Arbeitszeit gebucht.<br>" +
                            "<a href=\"" + frappe.utils.get_url() + "/desk#Form/OTRSConnect%20Article/" + article_name.name +
                            "\"><b>fehlerhaften OTRS Article aufrufen</b></a>" )

            if "remote" in description_lines or "Remote" in description_lines:
                item = user.erpnext_rs_item
            description = ("Arbeitszeit zu Ticket#" + ticket.tn + "<br>"
                            "Mitarbeiter: " + employee_name + "<br>"
                            "Erfasst: " + article.create_time.strftime("%d.%m.%Y %H:%M") + "<br>"
                            + description)
            #item_doc = frappe.get_doc("Item", item.name)
            delivery_note_item = frappe.get_doc({"doctype": "Delivery Note Item",
                                                "item_code": item,
                                                "description": description,
                                                "qty": float(article.time_unit) / float(4),
                                                })
            delivery_note_itmes_list.append(delivery_note_item)
        return delivery_note_itmes_list

    def set_delivery_note_for_tickets(self):
        settings = frappe.get_doc("OTRSConnect Settings")
        ERPNext_fetched_tickets = frappe.get_all("OTRSConnect Ticket", filters={"status": "fetched",
                                                                                "erpnext_customer": ("!=", "")})
        print(len(ERPNext_fetched_tickets))
        run_count = 0
        for ticketname in ERPNext_fetched_tickets:
            percent = run_count * 100 / len(ERPNext_fetched_tickets)
            run_count += 1
            frappe.publish_progress(percent, "verarbeite Tickets")

            ticket_doc = frappe.get_doc("OTRSConnect Ticket", ticketname)
            delivery_notes = frappe.get_all("Delivery Note", filters={"title": settings.delivery_note_title,
                                                                        "customer": ticket_doc.erpnext_customer,
                                                                        "status": "Draft"})

            if len(delivery_notes) == 0:
                delivery_note_doc = frappe.get_doc({"doctype": "Delivery Note",
                                                    "customer": ticket_doc.erpnext_customer,
                                                    "title": settings.delivery_note_title,
                                                    "status": "Draft",
                                                    "company": frappe.get_doc("Global Defaults").default_company
                                                    })
                for item in self.get_items_for_delivery_note_from_articles(ticket_doc):
                    delivery_note_doc.append("items", item)
                delivery_note_doc.insert()
            else:
                delivery_note_doc = frappe.get_doc("Delivery Note", delivery_notes[0])
                for item in self.get_items_for_delivery_note_from_articles(ticket_doc):
                    delivery_note_doc.append("items", item)
                delivery_note_doc.save()
            ticket_doc.status = "delivered"
            ticket_doc.save()
            ticket_doc.submit()
        frappe.msgprint(str(run_count) + " Tickets verarbeitet.")



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
        otrsdb = get_db(host=settings.otrs_host, user=settings.db_user, password=settings.db_password)
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
                print(frappe_doctype_dict)
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

    def create_delivery_notes(self):
        self.set_delivery_note_for_tickets()
