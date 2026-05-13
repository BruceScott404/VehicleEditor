import re
import subprocess
import threading
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import time
import os
import sys


if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).parent

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(base / "pw-browsers")

from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

def resource_path(relative_path):
    """
    Get absolute path to resource for both:
    - macOS (.app bundle)
    - Windows (.exe)
    """

    # Running as PyInstaller bundle
    if getattr(sys, "frozen", False):

        # macOS
        if sys.platform == "darwin":
            base_path = getattr(
                sys,
                "_MEIPASS",
                os.path.join(
                    os.path.dirname(sys.executable),
                    "..",
                    "Resources"
                )
            )

        # Windows
        elif sys.platform == "win32":
            base_path = getattr(
                sys,
                "_MEIPASS",
                os.path.dirname(sys.executable)
            )

        # Fallback for Linux/other systems
        else:
            base_path = getattr(
                sys,
                "_MEIPASS",
                os.path.dirname(sys.executable)
            )

    # Running in normal Python environment
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.abspath(os.path.join(base_path, relative_path))


def app_path(relative_path):
    """
    Read/write files that should live beside the executable.
    """
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


LOGIN_INFO_FILE=app_path("login_info.cfg")
TEXT_ADD_FILE=app_path("text_add.cfg")
MAKES_FILE=app_path("makes.cfg")
TYPES_FILE=app_path("types.cfg")

DEFAULT_MAKES = [
    "ALUMACRAFT",
    "Can-Am",
    "Lynx",
    "MANITOU",
    "MERCURY",
    "Sea-Doo",
    "Ski-Doo",
    "WIDESCAPE"
]

DEFAULT_TYPES = [
    "ATV",
    "Boats",
    "Motorcycles",
    "Outboard Motors",
    "Side-by-side",
    "Snowmobiles",
    "Watercrafts"
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("Vehicle Automator")
        self.geometry("600x400")
        self.minsize(600, 800)

        self.header = ctk.CTkFrame(
            self,
        )
        self.header.pack()

        self.logo = ctk.CTkImage(
            dark_image=Image.open(resource_path("resources/logo.png")),
            light_image=Image.open(resource_path("resources/logo.png")),
            size=(160,62)
        )

        self.logo_label = ctk.CTkLabel(
            self.header,
            text="",
            image=self.logo
        )
        self.logo_label.pack()
        

        self.login_info_button = ctk.CTkButton(
            self,
            text="View/Edit PowerGo Login Info",
            command=self.on_login_info_button_pressed,
            width=100,
            height=20
        )
        self.login_info_button.pack(pady=5)

        # Main container frame
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=30, pady=30)

        # Title
        self.title_label = ctk.CTkLabel(
            frame,
            text="Vehicle Automator Tool",
            font=("Arial", 24, "bold")
        )
        self.title_label.pack(pady=(10, 30))

        makes = self.get_makes()
        types = self.get_types()

        self.make_entry = ctk.CTkComboBox(
            frame, 
            width=350, 
            values=makes, 
            command=self.on_make_or_type_edited,
            state="readonly"
        )
        self.make_entry.pack(pady=20)

        self.type_entry = ctk.CTkComboBox(
            frame, 
            width=350,
            values=types,
            state="readonly",
            command=self.on_make_or_type_edited
        )
        self.type_entry.pack(pady=20)
        self.type_entry.set("Select Type")
        self.make_entry.set("Select Make")

        add_text_title_frame = ctk.CTkFrame(
            frame
        )
        add_text_title_frame.pack(expand=True,pady=10)

        self.add_text_label = ctk.CTkLabel(
            add_text_title_frame,
            text="Disclaimer text to add",
            font=("Arial", 18, "bold")
        )
        self.add_text_label.pack(pady=10, padx=10)

        self.add_text_edit_button = ctk.CTkButton(
            add_text_title_frame,
            text="Edit",
            command=self.on_add_text_edit_button_click
        )
        self.add_text_edit_button.pack(pady=10)

        self.add_text_preview = ctk.CTkTextbox(
            frame
        )
        self.add_text_preview.pack(pady=10, fill="both", expand=True)

        add_text = self.get_text_add()

        # Insert the add text into the text preview
        self.add_text_preview.insert("1.0", add_text)

        # Make it read-only
        self.add_text_preview.configure(state="disabled")

        # Run button
        self.run_button = ctk.CTkButton(
            frame,
            text="Run Automation",
            command=self.on_run_button_click,
            width=200,
            height=40
        )
        self.run_button.pack(pady=25)

        self.run_button.configure(state="disabled")
        if not makes:
            self.set_status("Please add some makes...")
        if not types:
            self.set_status("Please add some types...")

        # Status label
        self.status_label = ctk.CTkLabel(
            frame,
            text="Ready",
            font=("Arial", 14)
        )
        self.status_label.pack(pady=20)

    def set_status(self, text):
        """Safely update status label from any thread."""
        self.after(0, lambda: self.status_label.configure(text=text))

    def set_button_state(self, enabled: bool):
        """Enable or disable the run button from any thread."""
        state = "normal" if enabled else "disabled"
        self.after(0, lambda: self.run_button.configure(state=state))

    def on_make_or_type_edited(self, event):
        current_make = self.make_entry.get()
        current_type = self.type_entry.get()

        good = current_make != "Select Type" and current_type != "Select Type"
        self.set_button_state(good)

    def on_add_text_edit_button_click(self):
        current_text = self.get_text_add()

        self.open_text_add_edit_form(current_text)

        current_text = self.get_text_add()

        self.add_text_preview.configure(state="normal")
        self.add_text_preview.delete("1.0", "end")
        self.add_text_preview.insert("1.0", current_text)
        self.add_text_preview.configure(state="disabled")

    def on_login_info_button_pressed(self):

        current_info = self.get_login_info()
        email = ""
        password = ""
        if not (current_info == None):
            email = current_info[0]
            password = current_info[1]
        self.open_login_info_form(email,password)

    def on_run_button_click(self):
        # Get values from the text boxes
        make = self.make_entry.get().strip()
        vehicle_type = self.type_entry.get().strip()

        # Basic validation
        if not make or not vehicle_type:
            self.status_label.configure(
                text="Please enter both make and vehicle type."
            )
            return

        # Disable button while running
        self.run_button.configure(state="disabled")
        self.status_label.configure(
            text=f"Running automation for {make} {vehicle_type}..."
        )

        # Run automation in a background thread so UI stays responsive
        thread = threading.Thread(
            target=self.run_automation_thread,
            args=(make, vehicle_type),
            daemon=True
        )
        thread.start()

    def open_error_popup(self, error_text):
        popup = ctk.CTkToplevel(self)
        popup.title("ERROR")
        popup.geometry("400x400")
        
        popup.transient(self)
        popup.grab_set()
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 125
        popup.geometry(f"400x400+{x}+{y}")

        self.error_output = ctk.CTkTextbox(
            popup
        )
        self.error_output.pack(pady=10, fill="both", expand=True)
        self.error_output.insert("1.0", error_text)
        self.error_output.configure(state="disabled")

        def submit():
            popup.destroy()

        def on_close():
            popup.destroy()

        # Submit button
        submit_button = ctk.CTkButton(
            popup,
            text="Ok",
            command=submit
        )
        submit_button.pack(pady=20)

        # Enter key submits form
        popup.bind("<Return>", lambda event: submit())

        # Handle window close button
        popup.protocol("WM_DELETE_WINDOW", on_close)

        # Wait until popup is closed
        self.wait_window(popup)
        

    def open_text_add_edit_form(self, current_add_text):
        popup = ctk.CTkToplevel(self)
        popup.title("Edit Add Text")
        popup.geometry("400x400")
        
        popup.transient(self)
        popup.grab_set()
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 125
        popup.geometry(f"400x400+{x}+{y}")

        # Title
        title_label = ctk.CTkLabel(
            popup,
            text="Editing Text to Add",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=(20, 20))

        self.add_text_edit = ctk.CTkTextbox(
            popup
        )
        self.add_text_edit.pack(pady=10, fill="both", expand=True)
        self.add_text_edit.insert("1.0", current_add_text)
        

        def submit():
            with open(TEXT_ADD_FILE, "w") as lf:
                lf.write(self.add_text_edit.get("1.0", "end-1c"))
            popup.destroy()

        def on_close():
            popup.destroy()

        # Submit button
        submit_button = ctk.CTkButton(
            popup,
            text="Submit",
            command=submit
        )
        submit_button.pack(pady=20)

        # Enter key submits form
        popup.bind("<Return>", lambda event: submit())

        # Handle window close button
        popup.protocol("WM_DELETE_WINDOW", on_close)

        # Focus email field
        self.add_text_edit.focus()

        # Wait until popup is closed
        self.wait_window(popup)


    def open_login_info_form(self, email, password):

        # Create popup window
        popup = ctk.CTkToplevel(self)
        popup.title("Login Information")
        popup.geometry("400x250")
        popup.resizable(False, False)

        # Make popup modal
        popup.transient(self)
        popup.grab_set()

        # Center popup over parent window
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 125
        popup.geometry(f"400x250+{x}+{y}")

        # Title
        title_label = ctk.CTkLabel(
            popup,
            text="Enter PowerGo Login Information",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=(20, 20))

        # Email input
        email_entry = ctk.CTkEntry(
            popup,
            width=300,
            placeholder_text="Email"
        )
        email_entry.pack(pady=10)
        email_entry.insert(0,email)

        # Password input
        password_entry = ctk.CTkEntry(
            popup,
            width=300,
            placeholder_text="Password"
        )
        password_entry.pack(pady=10)
        password_entry.insert(0,password)
        

        def submit():
            with open(LOGIN_INFO_FILE, "w") as lf:
                lf.write(str(email_entry.get().strip()) + "\n")
                lf.write(str(password_entry.get().strip()) + "\n")
            popup.destroy()

        def on_close():
            popup.destroy()

        # Submit button
        submit_button = ctk.CTkButton(
            popup,
            text="Submit",
            command=submit
        )
        submit_button.pack(pady=20)

        # Enter key submits form
        popup.bind("<Return>", lambda event: submit())

        # Handle window close button
        popup.protocol("WM_DELETE_WINDOW", on_close)

        # Focus email field
        email_entry.focus()

        # Wait until popup is closed
        self.wait_window(popup)


    def run_automation_thread(self, make, vehicle_type):
        try:
            with sync_playwright() as playwright:
                self.run(playwright, make, vehicle_type)

            self.set_status("Automation complete.")
        except Exception as e:
            self.open_error_popup(e)
            self.set_status(f"Error")
        finally:
            self.set_button_state(True)

    
    def get_makes(self):
        if not os.path.exists(MAKES_FILE):
            with open(MAKES_FILE, "w") as f:
                makes = []

                for dm in DEFAULT_MAKES:
                    makes.append(dm)
                    f.write(str(dm) + "\n")
                return makes
        with open(MAKES_FILE, "r") as f:
            makes = []
            lines = f.readlines()
            for l in lines:
                makes.append(l.strip())

            if len(makes) == 0:
                return None
            return makes
        
    
    def get_types(self):
        if not os.path.exists(TYPES_FILE):
            with open(TYPES_FILE, "w") as f:
                types = []

                for dt in DEFAULT_TYPES:
                    types.append(dt)
                    f.write(str(dt) + "\n")
                return types
        with open(TYPES_FILE, "r") as f:
            types = []
            lines = f.readlines()
            for l in lines:
                types.append(l.strip())
            if len(types) == 0:
                return None
            return types

    
    def get_text_add(self):
        if not os.path.exists(TEXT_ADD_FILE):
            with open(TEXT_ADD_FILE, "w") as f:
                return ""
        with open(TEXT_ADD_FILE, "r") as f:
            result = ""
            lines = f.readlines()
            for l in lines:
                result += l
            return result

        
    def get_login_info(self):
        # Returns True only if it's a file
        if not os.path.exists(LOGIN_INFO_FILE):
            return None
        with open(LOGIN_INFO_FILE, "r") as f:
            lines = f.readlines()
            if len(lines) != 2:
                return None
            email = lines[0].strip()
            password = lines[1].strip()
            return (email,password)

    def run(self, playwright: Playwright, selected_make, selected_type) -> None:

        selected_make = selected_make.lower()
        selected_type = selected_type.lower()

        login_info = self.get_login_info()
        if login_info == None:
            raise Exception("Login info not found...")
        
        email = login_info[0]
        password = login_info[1]

        add_text = self.get_text_add()

        if add_text == "":
            raise Exception("Please add some text to add...")

        print("Text loaded: \n```")
        print(add_text)
        print("```")

        self.set_status("Opening browser...")

        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.powergo.ca/en/client-login/")
        with page.expect_popup() as page1_info:
            page.get_by_role("link", name="Access my account").first.click()
        page1 = page1_info.value

        page1.get_by_role("textbox", name="* Email").click()
        page1.get_by_role("textbox", name="* Email").fill(email)
        page1.get_by_role("textbox", name="* Email").press("Tab")
        page1.get_by_role("textbox", name="* Password").fill(password)
        page1.get_by_role("button", name="Login").click()

        page1.wait_for_load_state("networkidle")

        try:
            page1.get_by_text(
                "Invalid email address and/or password.",
                exact=True
            ).wait_for(timeout=3000)

            raise ValueError("Login failed: invalid email address and/or password.")

        except PlaywrightTimeoutError:
            pass

        page1.get_by_text("Show more filters ", exact=True).click()

        # Change type


        # Change Make
        make_dropdown = page1.locator("#make")

        page1.wait_for_function("""
        () => document.querySelector("#make")?.options.length > 1
        """)

        page1.wait_for_load_state("networkidle")

        make_dropdown = page1.locator("#make")

        options = make_dropdown.evaluate("""
        select => Array.from(select.options)
            .filter(o => o.hasAttribute("value") && o.value.trim() !== "")
            .map(o => ({
                value: o.value.toLowerCase(),
                text: o.textContent.trim()
            }))
        """)
        val = None
        for o in options:
            if o.get("text").lower() == selected_make:
                val = o.get('value')

        if val == None:
            error_message = f"MAKE [{selected_make}] NOT FOUND, MAKES INCLUDE: \n"
            for o in options:
                error_message += str(o.get("text")) + "\n"
            raise Exception(error_message)
        

        make_dropdown.select_option(val)

        state_dropdown = page1.locator("#state")
        state_dropdown.select_option("179")

        page1.wait_for_load_state("networkidle")

        type_dropdown = page1.locator("#item_type")

        page1.wait_for_function("""
        () => document.querySelector("#item_type")?.options.length > 1
        """)

        page1.wait_for_load_state("networkidle")
        options = type_dropdown.evaluate("""
        select => Array.from(select.options)
            .filter(o => o.hasAttribute("value") && o.value.trim() !== "")
            .map(o => ({
                value: o.value.toLowerCase(),
                text: o.textContent.trim()
            }))
        """)
        val = None
        for o in options:
            if o.get("text").lower() == selected_type:
                val = o.get('value')

        if val == None:
            error_message = f"TYPE [{selected_type}] NOT FOUND, TYPES INCLUDE: \n"
            for o in options:
                error_message += (str(o.get("text")) + "\n")
            raise Exception(error_message)

        type_dropdown.select_option(val)

        page1.wait_for_selector("td.stock-num-column a")

        page1.pause()

        all_links_scraped = False
        links = []
        prev_last = None
        while all_links_scraped == False:

            if prev_last != None:
                now_loaded = False
                while now_loaded == False:
                    new_links = page1.locator("td.stock-num-column a").evaluate_all("""
                    anchors => anchors.map(a => ({
                        stock: a.textContent.trim(),
                        href: a.href
                    }))
                    """)
                    if (new_links[len(new_links) - 1].get("stock") != prev_last):
                        now_loaded = True
                    self.set_status("Waiting for load")
                    time.sleep(1)
            page1.wait_for_load_state("networkidle")

            new_links = page1.locator("td.stock-num-column a").evaluate_all("""
            anchors => anchors.map(a => ({
                stock: a.textContent.trim(),
                href: a.href
            }))
            """)
            prev_last = new_links[len(new_links) - 1].get("stock")

            for l in new_links:
                links.append(l)

            next_button = page1.locator(
                "li.VuePagination__pagination-item-next-page",
                has=page1.locator("a.page-link", has_text=">")
            ).first

            is_disabled = next_button.evaluate("""
            el =>
                el.className.toLowerCase().includes('disabled') ||
                el.getAttribute('aria-disabled') === 'true'
            """)

            if is_disabled:
                all_links_scraped = True
                continue
            next_button.click()

        curr = 0
        for l in links:  
            curr += 1
            self.set_status(f"{curr}: {l}")      

        self.set_status(f"Loaded {len(links)} vehicles...")

        total = 0

        for i, item in enumerate(links):
            total += 1
            if total > 10000:
                    return
            self.set_status(f"{i + 1}/{len(links)} - Opening {item['stock']}")

            page1.goto(item["href"])
            page1.wait_for_load_state("networkidle")
            editor = page1.locator('iframe[title="Rich Text Area"]').content_frame.get_by_label(
                "Rich Text Area. Press ALT-0"
            )

            current_text = editor.evaluate("""
            el => el.innerText
            """)

            normalized_current = "".join(current_text.split()).lower()
            normalized_add = "".join(add_text.split()).lower()

            # Check if text already exists
            if normalized_add in normalized_current:
                self.set_status("Text already present, skipping.")
                continue

            # Click into editor
            editor.click()

            editor.evaluate(f"""
            (el) => {{
                el.focus();
                const range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);

                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            }}
            """)

            editor.press("Enter")
            editor.press("Enter")

            editor.type(add_text)

            page1.get_by_role("button", name="Save").click()
            page1.wait_for_load_state("networkidle")
            self.set_status("text added")
        # ---------------------
        context.close()
        browser.close()

if __name__ == "__main__":
    

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme(resource_path("resources/theme_data.json"))

    app = App()
    app.mainloop()