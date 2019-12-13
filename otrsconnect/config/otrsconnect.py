from __future__ import unicode_literals
from frappe import _

def get_data():

    return [
        {
            "label": _("OTRS Connect"),
            "icon": "octicon octicon-file-symlink-file",
            "items": [
                {
                    "type": "doctype",
                    "name": "OTRSConnect Article",
                    "label": _("OTRSConnect Article"),
                },
                {
                    "type": "doctype",
                    "name": "OTRSConnect Ticket",
                    "label": _("OTRSConnect Ticket"),
                },
                {
                    "type": "doctype",
                    "name": "OTRSConnect User",
                    "label": _("OTRSConnect User"),
                },
                {
                    "type": "doctype",
                    "name": "OTRSConnect Functions",
                    "label": _("OTRSConnect Functions"),
                },
                {
                    "type": "doctype",
                    "name": "OTRSConnect Settings",
                    "label": _("OTRSConnect Settings"),
                }
            ]
        }
    ]