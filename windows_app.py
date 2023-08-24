import pkg_resources
import webbrowser
import subprocess
import tkinter as tk
from tkinter import messagebox
import psutil
from infi.systray import SysTrayIcon

class AppGUI:
    processes = []

    def __init__(self, root):
        self.root = root
        self.root.title("Documents Search")

        self.run_app("main")
        self.run_app("add_documents")

        menu_options = (
            ("Open search engine", None, self.open_browser),
        )

        self.sys_tray_icon = SysTrayIcon("ico.ico", "Documents Search", menu_options, on_quit=self.on_quit)
        self.sys_tray_icon.start()

    def open_browser(self, systray=None):
        webbrowser.open("http://127.0.0.1:5000")

    def on_quit(self, systray):
        self.terminate_processes()

    def terminate_processes(self):
        for proc in self.processes:
            self.terminate_child_processes(proc)
            proc.terminate()
            proc.wait()

    def terminate_child_processes(self, parent_process):
        parent = psutil.Process(parent_process.pid)
        for child in parent.children(recursive=True):
            child.terminate()

    def run_app(self, app_name):
        proc = subprocess.Popen(["python3", app_name + ".py"])
        self.processes.append(proc)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Nasconde la finestra di Tkinter
    app = AppGUI(root)