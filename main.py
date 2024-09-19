import os
import json
import subprocess
import tkinter.messagebox as messagebox
import re
from pathlib import Path
import base64
import logging
from tkinter import filedialog, Listbox

# Logging setup
APPDATA_DIR = Path(os.getenv('APPDATA')) / "Falcon" / "Falcon Remote"
LOG_FILE = APPDATA_DIR / 'app.log'
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR)

def safe_action(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    return wrapper

# Function to install missing libraries
def install_libraries():
    try:
        import customtkinter
        import pywin32
        from cryptography.fernet import Fernet
    except ImportError:
        print("Bibliotheken werden installiert...")
        subprocess.check_call(["pip", "install", "customtkinter", "pywin32", "cryptography"])

# Install missing libraries before proceeding
install_libraries()

import customtkinter as ctk
from cryptography.fernet import Fernet

# Set up AppData directory to store servers and encryption keys
SERVER_DATA_FILE = APPDATA_DIR / "servers.json"
KEY_FILE = APPDATA_DIR / "key.key"

# Create directories if they don't exist
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

# Generate or load Fernet encryption key
def generate_or_load_key():
    if not KEY_FILE.exists():
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as key_file:
            key_file.write(key)
    else:
        with open(KEY_FILE, 'rb') as key_file:
            key = key_file.read()
    return key

# Initialize the Fernet encryption object
fernet_key = generate_or_load_key()
fernet = Fernet(fernet_key)

# Encrypt server data
def encrypt_data(data):
    return fernet.encrypt(json.dumps(data).encode()).decode()

# Decrypt server data
def decrypt_data(data):
    try:
        return json.loads(fernet.decrypt(data.encode()).decode())
    except Exception:
        return []

# Create default server data file if it doesn't exist
if not SERVER_DATA_FILE.exists():
    with open(SERVER_DATA_FILE, 'w') as f:
        encrypted_data = encrypt_data([])
        f.write(encrypted_data)

# Load server data (decrypt)
def load_servers():
    with open(SERVER_DATA_FILE, 'r') as f:
        encrypted_data = f.read()
        return decrypt_data(encrypted_data)

# Save server data (encrypt)
def save_servers(servers):
    encrypted_data = encrypt_data(servers)
    with open(SERVER_DATA_FILE, 'w') as f:
        f.write(encrypted_data)

#-----------------------

# Launch remote desktop connection (RDP)
def connect_to_server(ip, username, password):
    command = f"cmdkey /generic:{ip} /user:{username} /pass:{password}"
    subprocess.run(command, shell=True)
    subprocess.run(f"mstsc /v:{ip}", shell=True)

# Validate IP address format
def is_valid_ip(ip):
    pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    return pattern.match(ip)

# Backup and restore functions
def backup_data():
    backup_file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if backup_file:
        with open(backup_file, 'w') as f:
            f.write(open(SERVER_DATA_FILE, 'r').read())
        messagebox.showinfo("Backup", "Server Daten wurden abgespeichert!")

def restore_data():
    restore_file = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if restore_file:
        with open(SERVER_DATA_FILE, 'w') as f:
            f.write(open(restore_file, 'r').read())
        app.servers = load_servers()
        app.load_server_list()
        messagebox.showinfo("Restore", "Server Daten wurden wiederhergestellt!")

class FalconRemoteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Falcon Remote")
        self.geometry("600x800")  # Set main window to 600x800 pixels
        self.servers = load_servers()

        # Set dark theme
        ctk.set_appearance_mode("dark")

        # Use valid color values
        fg_color = "gray92"
        text_color = "gray14"
        selectbackground = "blue"
        selectforeground = "white"

        # Server list frame
        self.server_frame = ctk.CTkFrame(self)
        self.server_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Font settings for the listbox
        listbox_font = ("Helvetica", 12)  # Set the font size to 12

        # Server listbox
        self.server_listbox = Listbox(self.server_frame, bg="gray20", fg="white", selectbackground="white", selectforeground="black", font=listbox_font)
        self.server_listbox.pack(pady=10, padx=10, fill="both", expand=True)
        self.server_listbox.bind("<<ListboxSelect>>", self.on_server_select)

        # Buttons arranged in the specified order
        self.connect_button = ctk.CTkButton(self, text="Verbinden", command=self.connect_to_selected_server)
        self.connect_button.pack(pady=10)

        self.add_button = ctk.CTkButton(self, text="Hinzufügen", command=self.open_add_server_window)
        self.add_button.pack(pady=10)

        self.edit_button = ctk.CTkButton(self, text="Bearbeiten", command=self.open_edit_server_window)
        self.edit_button.pack(pady=10)

        self.delete_button = ctk.CTkButton(self, text="Löschen", command=self.delete_server)
        self.delete_button.pack(pady=10)

        self.backup_button = ctk.CTkButton(self, text="Backup", command=backup_data)
        self.backup_button.pack(pady=10)

        self.restore_button = ctk.CTkButton(self, text="Wiederherstellen", command=restore_data)
        self.restore_button.pack(pady=10)

        # Status indicators
        self.server_details_label = ctk.CTkLabel(self, text="Details")
        self.server_details_label.pack(pady=10)

        # Load servers into the listbox
        self.load_server_list()

    # Load servers into the listbox
    def load_server_list(self):
        self.server_listbox.delete(0, 'end')

        # Get the width of the listbox and font
        listbox_width = self.server_listbox.winfo_width()
        font = self.server_listbox.cget("font")

        for server in self.servers:
            server_name = server['name']

            # Calculate text width
            text_width = self.server_listbox.tk.call("font", "measure", font, server_name)

            # Calculate the left padding needed to center the text
            padding = (listbox_width - text_width) // 2
            padded_server_name = f"{' ' * (padding // 6)}{server_name}"  # Divide padding by 6 for proportional spacing

            self.server_listbox.insert('end', padded_server_name)

    # Add server
    def open_add_server_window(self):
        self.add_window = AddServerWindow(self, self.add_server)

    @safe_action
    def add_server(self, name, ip, username, password):
        if not is_valid_ip(ip):
            self.add_window.show_error("Bitte gebe eine richtige IP an!")
            return

        new_server = {
            "name": name,
            "ip": ip,
            "username": username,
            "password": password
        }
        self.servers.append(new_server)
        save_servers(self.servers)
        self.load_server_list()
        self.add_window.destroy()  # Close the window after successful save

    # Edit server
    def open_edit_server_window(self):
        selected_index = self.server_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Achtung", "Kein Server Ausgewählt")
            return

        selected_index = selected_index[0]
        selected_server = self.servers[selected_index]
        self.edit_window = EditServerWindow(self, selected_server, self.update_server, selected_index)

    @safe_action
    def update_server(self, index, name, ip, username, password):
        if not is_valid_ip(ip):
            self.edit_window.show_error("Bitte gebe eine richtige IP an!")
            return

        self.servers[index] = {
            "name": name,
            "ip": ip,
            "username": username,
            "password": password
        }
        save_servers(self.servers)
        self.load_server_list()
        self.edit_window.destroy()  # Close the window after successful update

    # Delete server
    @safe_action
    def delete_server(self):
        selected_index = self.server_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Achtung", "Kein Server Ausgewählt")
            return

        selected_index = selected_index[0]
        del self.servers[selected_index]
        save_servers(self.servers)
        self.load_server_list()

    # Connect to the selected server
    @safe_action
    def connect_to_selected_server(self):
        selected_index = self.server_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Achtung", "Kein Server Ausgewählt")
            return

        selected_server = self.servers[selected_index[0]]
        connect_to_server(selected_server['ip'], selected_server['username'], selected_server['password'])

    # Handle server selection
    def on_server_select(self, event):
        selected_index = self.server_listbox.curselection()
        if selected_index:
            server = self.servers[selected_index[0]]
            self.server_details_label.configure(text=f"IP: {server['ip']}\nUsername: {server['username']}")

class AddServerWindow(ctk.CTkToplevel):
    def __init__(self, parent, save_callback):
        super().__init__(parent)
        self.save_callback = save_callback
        self.title("Hinzufügen")
        self.geometry("600x800")  # Set add server window to 600x800 pixels

        # Ensure this window stays on top of the main window
        self.attributes("-topmost", True)

        # Error message label
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack(pady=5)

        self.name_label = ctk.CTkLabel(self, text="Server Name")
        self.name_label.pack(pady=10)
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.pack(pady=10)

        self.ip_label = ctk.CTkLabel(self, text="IP Address")
        self.ip_label.pack(pady=10)
        self.ip_entry = ctk.CTkEntry(self)
        self.ip_entry.pack(pady=10)

        self.username_label = ctk.CTkLabel(self, text="Username")
        self.username_label.pack(pady=10)
        self.username_entry = ctk.CTkEntry(self)
        self.username_entry.pack(pady=10)

        self.password_label = ctk.CTkLabel(self, text="Passwort")
        self.password_label.pack(pady=10)
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.pack(pady=10)

        self.save_button = ctk.CTkButton(self, text="Speichern", command=self.save_server)
        self.save_button.pack(pady=20)

    def save_server(self):
        name = self.name_entry.get()
        ip = self.ip_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not name or not ip or not username or not password:
            self.show_error("Du musst alles ausfüllen!")
            return

        if not is_valid_ip(ip):
            self.show_error("Bitte gebe eine richtige IP an!")
            return

        self.save_callback(name, ip, username, password)
        self.destroy()

    def show_error(self, message):
        self.error_label.configure(text=message)

class EditServerWindow(AddServerWindow):
    def __init__(self, parent, server_data, save_callback, index):
        super().__init__(parent, save_callback)
        self.index = index
        self.title("Bearbeiten")

        # Pre-fill the fields with the existing server data
        self.name_entry.insert(0, server_data['name'])
        self.ip_entry.insert(0, server_data['ip'])
        self.username_entry.insert(0, server_data['username'])
        self.password_entry.insert(0, server_data['password'])

    def save_server(self):
        name = self.name_entry.get()
        ip = self.ip_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not name or not ip or not username or not password:
            self.show_error("Alle Felder müssen ausgefüllt sein!")
            return

        if not is_valid_ip(ip):
            self.show_error("Bitte gebe eine richtige IP an!")
            return

        self.save_callback(self.index, name, ip, username, password)
        self.destroy()

    def show_error(self, message):
        self.error_label.configure(text=message)


def is_valid_ip(ip):
    try:
        import ipaddress
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    app = FalconRemoteApp()
    app.mainloop()