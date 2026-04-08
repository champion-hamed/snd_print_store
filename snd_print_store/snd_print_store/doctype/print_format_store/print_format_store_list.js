frappe.listview_settings['Print Format Store'] = {
    refresh: function(listview) {
        listview.page.remove_inner_button(__('Sync Print Formats'));

        listview.page.add_inner_button(__('Sync Print Formats'), () => {
            const selected = listview.get_checked_items();
            
            if (selected.length > 0) {
                frappe.confirm(
                    __('Sync the selected ({0}) Print Formats from the Hub?', [selected.length]), 
                    () => { this.run_sync_selected(listview, selected); }
                );
            } else {
                frappe.confirm(
                    __('Sync all available Print Formats from the Hub?'), 
                    () => { this.run_sync_all(listview); }
                );
            }
        }).addClass('btn-primary');
    },

    get_indicator: function(doc) {
        if (doc.status === "Up to Date") {
            return [__("Up to Date"), "green", "status,=,Up to Date"];
        } else if (doc.status === "Update Available") {
            return [__("Update Available"), "orange", "status,=,Update Available"];
        } else {
            return [__("Not Installed"), "gray", "status,=,Not Installed"];
        }
    },

    dropdown_button: {
        get_label: __("Actions"),
        buttons: [
            {
                get_label: __("Sync"), 
                show: function(doc) {
                    return doc.status !== "Up to Date";
                },
                action: function(doc) {
                    frappe.call({
                        method: "snd_print_store.snd_print_store.doctype.print_format_store.print_format_store.install_remote_format",
                        args: { format_name: doc.name },
                        freeze: true,
                        callback: () => {
                            listview.refresh(); // Doesn't work. Try to fix it.
                        }
                    });
                }
            },
            {
                get_label: __("Preview Image"),
                show: function(doc) {
                    return !!doc.preview_image;
                },
                action: function(doc) {
                    let d = new frappe.ui.Dialog({
                        title: doc.name,
                        size: 'extra-large',
                    });
                    d.$body.html(`<div style="text-align: center; padding: 10px;">
                        <img src="${doc.preview_image}" style="width: 100%; border-radius: 4px;">
                    </div>`);
                    d.show();
                }
            }
        ]
    },

    run_sync_selected: function(listview, selected) {
        let promises = selected.map(doc => {
            return frappe.call({
                method: "snd_print_store.snd_print_store.doctype.print_format_store.print_format_store.install_remote_format",
                args: { format_name: doc.name },
                freeze: true
            });
        });

        Promise.all(promises).then(() => {
            frappe.show_alert({message: __('Selected print formats synced successfully'), indicator: 'green'});
            listview.refresh();
        });
    },

    run_sync_all: function(listview) {
        frappe.call({
            method: "snd_print_store.snd_print_store.doctype.print_format_store.print_format_store.bulk_sync",
            freeze: true,
            freeze_message: __("Syncing all print formats..."),
            callback: (r) => {
                if(!r.exc) {
                    frappe.show_alert({message: __('All print formats synced successfully'), indicator: 'green'});
                    listview.refresh();
                }
            }
        });
    }
};