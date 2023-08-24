import webbrowser
import subprocess
import rumps

class AppGUI(rumps.App):
    processes = []

    def __init__(self):
        super(AppGUI, self).__init__("Documents search", quit_button=None)
        self.run_app("main")
        self.run_app("add_documents")

    @rumps.clicked("Open search engine")
    def open_browser(self, _):
        webbrowser.open("http://127.0.0.1:5000")

    @rumps.clicked("Quit")
    def stop_app(self, _):
        self.terminate_processes()
        rumps.quit_application()

    def terminate_processes(self):
        for proc in self.processes:
            proc.terminate()

    def run_app(self, app_name):
        proc = subprocess.Popen(["python3", app_name + ".py"])
        self.processes.append(proc)

if __name__ == "__main__":
    app = AppGUI()
    app.run()
