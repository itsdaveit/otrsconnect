// Copyright (c) 2018, itsdave GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('OTRSConnect Ticket', {
	refresh: function(frm) {

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "OTRSConnect Settings",
                fieldname: ["zoom_link"]
            },
            callback(r) {
                console.log
                if(r.message) {
                    console.log(r.message)
                    frm.add_custom_button(__('OTRS Ticket Zoom'), function(){
                        window.open(r.message["zoom_link"] + cur_frm.doc.name,'_blank');;
                    }, __("Utilities"));
                }
            }
        });






	}

});
