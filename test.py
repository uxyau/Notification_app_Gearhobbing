import tkinter as tk
from tkinter import messagebox, scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
import glob


class FileHandler(FileSystemEventHandler):
    def __init__(self):
        self.count = 0
        self.last_file_name = ""

    def on_created(self, event):
        if event.is_directory:
            return

        self.count += 1
        if self.count % 1 == 0:
            self.show_message(event)

    def show_message(self, event):
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()  # Hide the main window

        response = messagebox.askokcancel("Meldung", "Bitte das Teil herausnehmen! Nach Herausnahme OK drücken.")
        if response:

            start_time = time.time()

            current_time = time.strftime("%Y-%m-%d %H:%M:%S")

            list_of_files = sorted(glob.glob(self.folder + "/*"))
            last_file = list_of_files[-1]

            needed_file = last_file

            if os.path.getctime(last_file) > start_time:
                needed_file = list_of_files[-2]

            qass_nr = needed_file.split("0025p")[1].split("c0b01")[0]

            txt_path = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/DoE_Oli_TXT_fuer_Messungen/last_added_file.txt"

            print(qass_nr + " wurde herausgenommen.")

            # Schreibe den Dateinamen in eine Textdatei
            with open(txt_path, 'a+') as file:
                file.write(current_time + ";" + qass_nr + "\n")

        root.destroy()


def watch_folder(folder_to_watch):
    event_handler = FileHandler()
    event_handler.folder = folder_to_watch
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    folder_to_watch = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/DoE_Verschleiss_Qass"
    watch_folder(folder_to_watch)