# Copyright (c) 2026, SANAD Digital and contributors
# For license information, please see license.txt

import frappe
import requests
import hashlib
from frappe import _
from frappe.model.document import Document

class PrintFormatStore(Document):
    def db_insert(self, *args, **kwargs): pass
    def db_update(self, *args, **kwargs): pass
    def delete(self, *args, **kwargs): pass

    def load_from_db(self):
        # 1. Fetch metadata and catalog list (to get the remote hash)
        catalog = call_hub_api("get_print_format_catalog")
        # Find this specific format in the catalog to get its content_hash
        remote_item = None
        for item in (catalog or []):
            if item.get("name") == self.name:
                remote_item = item
                break
        
        data = call_hub_api("get_print_metadata", {"name": self.name})
        
        if data:
            self.name = data.get("name")
            self.doc_type = data.get("doc_type")
            self.module = data.get("module")
            self.print_format_for = data.get("print_format_for")
            self.preview_image = data.get("preview_image")
            
            # 2. Check local status for the "- Hub" version
            local_name = self.name
            self.status = "Not Installed"
            
            if frappe.db.exists("Print Format", local_name):
                local_doc = frappe.get_doc("Print Format", local_name)
                
                # Generate local hash for comparison
                if data.get("custom_format"):
                    local_content = str(local_doc.html or "") + str(local_doc.css or "")
                else:
                    local_content = str(local_doc.format_data or "") + str(local_doc.css or "")

                local_hash = hashlib.sha256(local_content.encode()).hexdigest()
                if local_hash == remote_item.get("content_hash"):
                    self.status = "Up to Date"
                else:
                    self.status = "Update Available"

            # Add status to proplist so JS can see it
            self._proplist = ["name", "doc_type", "module", "print_format_for", "preview_image", "status"]

    @staticmethod
    def get_list(args):
        catalog = call_hub_api("get_print_format_catalog") or []

        for item in catalog:
            # Default status
            item['status'] = "Not Installed"
            
            if frappe.db.exists("Print Format", item['name']):
                local_doc = frappe.get_doc("Print Format", item['name'])
                
                if item.get("custom_format"):
                    local_content = str(local_doc.html or "") + str(local_doc.css or "")
                else:
                    local_content = str(local_doc.format_data or "") + str(local_doc.css or "")

                local_hash = hashlib.sha256(local_content.encode()).hexdigest()
                
                if local_hash == item.get("content_hash"):
                    item['status'] = "Up to Date"
                else:
                    item['status'] = "Update Available"

            # Inside your for loop in get_list:
            if item['status'] == "Update Available":
                item['button_label'] = "Update"
            elif item['status'] == "Not Installed":
                item['button_label'] = "Install"
            else:
                item['button_label'] = None
                    
        return catalog

    @staticmethod
    def get_count(filters=None, **kwargs): return 0
    @staticmethod
    def get_stats(**kwargs): pass

def call_hub_api(method, params=None):
    base_url = "https://hub.sanad.digital"
    api_path = "/api/method/snd_data_hub.api.snd_print_store."    
    url = base_url + api_path + method
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("message")
        return None
    except Exception:
        return None

@frappe.whitelist()
def install_remote_format(format_name):
    # Import inside to avoid circular dependencies if call_hub_api is in the same file
    from .print_format_store import call_hub_api
    
    code_data = call_hub_api("get_print_code", {"name": format_name})
    
    if not code_data:
        frappe.throw(_("Could not fetch source code from the Hub"))

    if frappe.db.exists("Print Format", format_name):
        local_doc = frappe.get_doc("Print Format", format_name)
    else:
        local_doc = frappe.new_doc("Print Format")
        # Add this line to set the primary document ID
        local_doc.name = format_name 
        local_doc.print_format_name = format_name

    local_doc.update({
        "print_format_for": code_data.get("print_format_for"), 
        "doc_type": code_data.get("doc_type"),
        "report": code_data.get("report"),
        "standard": "No", # Keeping your preference
        "custom_format": code_data.get("custom_format"),
        "print_format_type": code_data.get("print_format_type"),
        "html": code_data.get("html"),
        "css": code_data.get("css"),
        "format_data": code_data.get("format_data")
    })

    local_doc.save(ignore_permissions=True)
    
    return {
        "status": "success", 
        "message": _("Format {0} synced successfully").format(format_name)
    }

@frappe.whitelist()
def bulk_sync():
    from .print_format_store import call_hub_api
    import hashlib

    catalog = call_hub_api("get_print_format_catalog")
    if not catalog:
        return _("No formats found in Hub")

    synced_count = 0
    for item in catalog:
        name = item.get("name")        
        should_sync = False
        
        if not frappe.db.exists("Print Format", name):
            should_sync = True
        else:
            # Lean check: only sync if content changed
            doc = frappe.get_doc("Print Format", name)
            if item.get("custom_format"):
                content = str(doc.html or "") + str(doc.css or "")
            else:
                content = str(doc.format_data or "") + str(doc.css or "")

            local_hash = hashlib.sha256(content.encode()).hexdigest()

            if local_hash != item.get("content_hash"):
                should_sync = True
        
        if should_sync:
            install_remote_format(name)
            synced_count = synced_count + 1

    return _("Synced {0} formats").format(synced_count)