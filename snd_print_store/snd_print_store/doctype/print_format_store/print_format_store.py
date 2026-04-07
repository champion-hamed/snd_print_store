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
                html_str = str(local_doc.html or "")
                css_str = str(local_doc.css or "")
                local_content = html_str + css_str
                local_hash = hashlib.sha256(local_content.encode()).hexdigest()
                
                remote_hash = remote_item.get("content_hash") if remote_item else None
                
                if local_hash == remote_hash:
                    self.status = "Up to Date"
                else:
                    self.status = "Update Available"

            # Add status to proplist so JS can see it
            self._proplist = ["name", "doc_type", "module", "print_format_for", "preview_image", "status"]

    @staticmethod
    def get_list(args):
        return call_hub_api("get_print_format_catalog") or []

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
    from .print_format_store import call_hub_api
    code_data = call_hub_api("get_print_code", {"name": format_name})
    
    if not code_data:
        frappe.throw(_("Could not fetch source code from the Hub"))

    new_name = format_name
    
    if frappe.db.exists("Print Format", new_name):
        local_doc = frappe.get_doc("Print Format", new_name)
    else:
        local_doc = frappe.new_doc("Print Format")
        local_doc.name = new_name

    local_doc.update({
        "print_format_for": code_data.get("print_format_for"), 
        "doc_type": code_data.get("doc_type"),
        "report": code_data.get("report"),
        "standard": "No",
        "custom_format": code_data.get("custom_format"),
        "print_format_type": code_data.get("print_format_type"),
        "html": code_data.get("html"),
        "css": code_data.get("css"),
        "format_data": code_data.get("format_data")
    })

    local_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success", 
        "message": _("Format installed as {0}").format(new_name)
    }