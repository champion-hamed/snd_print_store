// Copyright (c) 2026, SANAD Digital and contributors
// For license information, please see license.txt

frappe.ui.form.on('Print Format Store', {
    refresh: function(frm) {
        // 1. Preview Image Logic
        if (frm.doc.preview_image) {
            let wrapper = frm.get_field('preview_html').$wrapper;
            wrapper.html(`
                <div class="preview-main-container" style="text-align: center; background: #fafbfc; border: 1px solid #d1d8dd; border-radius: 8px; padding: 15px;">
                    <img src="${frm.doc.preview_image}" 
                         class="hub-preview-img"
                         style="max-width: 100%; cursor: zoom-in; border-radius: 4px; border: 1px solid #eee; transition: transform 0.2s;" 
                         onclick="frappe.ui.form.handlers.enlarge_hub_image('${frm.doc.preview_image}', '${frm.doc.name}')">
                </div>
            `);
            
            wrapper.find('.hub-preview-img').hover(
                function() { $(this).css('transform', 'scale(1.01)'); },
                function() { $(this).css('transform', 'scale(1)'); }
            );
        }

        // 2. Smart Button / Status Logic
        frm.remove_custom_button(__('Install'));
        frm.remove_custom_button(__('Update'));
        frm.dashboard.clear_headline();

        if (frm.doc.status === "Up to Date") {
            frm.dashboard.set_headline_alert(
                `<div class="indicator green"><span>${__("This print format is already installed and up to date.")}</span></div>`
            );
        } else {
            let btn_label = frm.doc.status === "Update Available" ? __('Update') : __('Install');
            
            frm.add_custom_button(btn_label, function() {
                let confirm_msg = (btn_label === __('Update')) 
                    ? __('Updating will overwrite local changes. Continue?') 
                    : __('Do you want to install a copy of {0}?', [frm.doc.name]);

                frappe.confirm(confirm_msg, function() {
                    install_format(frm);
                });
            }).addClass('btn-primary');
        }
        if (["Update Available", "Up to Date"].includes(frm.doc.status)) {
            set_as_default(frm);
            go_to_print_format(frm);
        }
    }
});

function set_as_default(frm) {
    if (frm.doc.doc_type) {
        frappe.model.with_doctype(frm.doc.doc_type, function () {
            let current_format = frappe.get_meta(frm.doc.doc_type).default_print_format;
            if (current_format == frm.doc.name) {
                return;
            }
    
            frm.add_custom_button(__("Set as Default"), function () {
                frappe.call({
                    method: "frappe.printing.doctype.print_format.print_format.make_default",
                    args: {
                        name: frm.doc.name,
                    },
                    callback: function () {
                        frm.refresh();
                    },
                });
            });
        });
    }
}

function go_to_print_format(frm) {
    frm.add_custom_button(__('Go to Print Format'), function() {
        frappe.set_route("Form", "Print Format", frm.doc.name);
    })
}

frappe.ui.form.handlers.enlarge_hub_image = function(src, title) {
    let d = new frappe.ui.Dialog({
        title: title,
        size: 'extra-large',
    });
    d.$body.html(`<div style="text-align: center; padding: 10px;"><img src="${src}" style="width: 100%; height: auto; border-radius: 4px;"></div>`);
    d.show();
};

function install_format(frm) {
    frappe.call({
        method: "snd_print_store.snd_print_store.doctype.print_format_store.print_format_store.install_remote_format",
        args: { format_name: frm.doc.name },
        freeze: true,
        freeze_message: __("Downloading from Hub..."),
        callback: function(r) {
            if (r.message && r.message.status === "success") {
                frappe.show_alert({ message: r.message.message, indicator: 'green' });
                frm.reload_doc();
            }
        }
    });
}