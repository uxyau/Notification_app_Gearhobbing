import threading
import sys
sys.path.insert(0, '..')
import os
import time
import tkinter as tk
from tkinter import messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from qass.qassDecodeRaw import qassDecodeRaw



class FileHandler(FileSystemEventHandler):
    def __init__(self):
        self.count = 0

    def on_created(self, event):
        if event.is_directory:
            return

        self.count += 1
        if self.count % 40 == 0:
            self.show_message(event)

    def show_message(self, event):
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        response = messagebox.askokcancel("Meldung", "Bitte das Teil herausnehmen! Nach Herausnahme OK drücken.")
        if response:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print("Zeitpunkt:", current_time)

            self.last_file_name = os.path.basename(event.src_path)
            fname = Path(self.folder + "/" + self.last_file_name)
            data, file_header_map = qassDecodeRaw(fname)
            qass_nr = file_header_map["proc_cnt"]

            # Schreibe den Dateinamen in eine Textdatei
            with open("last_added_file.txt", "a+") as file:
                file.write(qass_nr + "\n")

        root.destroy()

def watch_folder(folder_to_watch):
    event_handler = FileHandler()
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
    folder_to_watch = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/Langzeituntersuchung_Oli"
    #folder_to_watch = "/Users/oliverschendel/GitHub Repos/Feature-Extraction-Qass/Quality_Data_Reany"
    watch_folder(folder_to_watch)