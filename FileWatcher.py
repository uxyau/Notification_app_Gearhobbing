import tkinter as tk
from tkinter import messagebox, scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
import glob

class FileHandler(FileSystemEventHandler):
    def __init__(self, app_textbox, teile_count_box, last_5_lines, folder_to_watch):
        self.count = 0
        self.app_textbox = app_textbox
        self.teile_count_box = teile_count_box
        self.last_5_lines = last_5_lines
        self.entnahme_frequenz = 1
        self.folder = folder_to_watch

    def on_created(self, event):
        if event.is_directory:
            return

        self.count += 1
        self.teile_count_box.config(text=f"Anzahl Teile bis zur \n nächsten Entnahme: \n{self.entnahme_frequenz - (self.count % self.entnahme_frequenz)}")
        if self.count % self.entnahme_frequenz == 0:
            self.show_message(event)

    def show_message(self, event):
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()

        response = messagebox.askokcancel("Meldung", "Bitte das Teil herausnehmen! Nach Herausnahme OK drücken.")
        if response:
                self.handle_file(event)

    def handle_file(self, event=None):
        start_time = time.time()

        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        list_of_files = sorted(glob.glob(self.folder + "/*"))
        last_file = list_of_files[-1]

        needed_file = last_file

        if os.path.getctime(last_file) > start_time:
            needed_file = list_of_files[-2]
        qass_nr = needed_file.split("0025p")[1].split("c0b01")[0]

        self.save_to_file(current_time, qass_nr)
        self.update_textbox(qass_nr + " wurde herausgenommen.")

    def save_to_file(self, current_time, qass_nr):
        txt_path = "/Volumes/sftpgwessbachfs/DoE_Oli_TXT_fuer_Messungen/last_added_file.txt"
        with open(txt_path, 'a+') as file:
            file.write(current_time + ";" + qass_nr + "\n")
            lines = file.readlines()
        last_5 = lines[-5:]
        formatted_text = '\n'.join([line.split(';')[1].strip() for line in last_5])
        self.last_5_lines.config(text=formatted_text)

    def update_textbox(self, message):
        #self.app_textbox.config(state=tk.NORMAL)
        #self.app_textbox.delete(1.0, tk.END)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.teile_count_box.insert(tk.END, message)
        self.teile_count_box.config(state=tk.DISABLED)


def watch_folder(folder_to_watch):
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.title("Ordnerüberwachung")
    root.geometry("600x300+10+10")  # Width x Height + x_offset + y_offset

    label1 = tk.Label(root, width=20, height=15, anchor='nw', justify='right', bg='white', relief='sunken')
    label1.pack(side=tk.RIGHT, padx=30, pady=10, fill=tk.BOTH, expand=True)

    app_textbox = scrolledtext.ScrolledText(label1, width=20, height=15, state=tk.DISABLED)
    app_textbox.pack(side=tk.RIGHT, padx=0, pady=0)

    teile_counter = tk.Label(label1, text="Anzahl Teile bis zur \n nächsten Entnahme: \n", width=20, height=4,
                                         relief='flat')
    teile_counter.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

    überschrift_last5 = tk.Label(label1, text="\n \n Die 5 letzten \nherausgenommenen Teile:", width=20, height=4, anchor='nw'
                                 , bg='white', relief='flat')
    überschrift_last5.pack(padx=20, pady=0, expand=False)

    last_5_lines = tk.Label(label1, width=20, height=20, bg='white', relief='sunken')
    last_5_lines.pack(padx=10, pady=10, expand=True)

    frame = tk.Frame(root)
    frame.pack(side=tk.RIGHT, padx=10, pady=10)

    def manual_removal():
        # Implement functionality of manual removal button
        event_handler.handle_file()

    def delete_last_line():
        txt_path = "/Volumes/sftpgwessbachfs/DoE_Oli_TXT_fuer_Messungen/last_added_file.txt"
        lines = []
        with open(txt_path, 'r') as file:
            lines = file.readlines()

        if lines:
            last_line = lines[-1]
            qass_nr = last_line.split(";")[1].strip()
            with open(txt_path, 'w') as file:
                file.writelines(lines[:-1])

            event_handler.update_textbox(qass_nr + " wurde gelöscht.")

        last_5 = lines[-5:]
        formatted_text = '\n'.join([line.split(';')[1].strip() for line in last_5])
        last_5_lines.config(text=formatted_text)

    tk.Button(frame, text="Manuelle Entnahme", command=manual_removal).pack(pady=10)
    tk.Button(frame, text="Zeile löschen", command=delete_last_line, fg="red").pack(pady=10)

    event_handler = FileHandler(app_textbox, teile_counter, last_5_lines, folder_to_watch)
    #event_handler.folder = folder_to_watch

    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

    #def on_closing():
    #    observer.stop()
    #    root.destroy()

    ##root.protocol("WM_DELETE_WINDOW", on_closing)
    #root.mainloop()

    #observer.join()


if __name__ == "__main__":
    folder_to_watch = "/Volumes/sftpgwessbachfs/DoE_Verschleiss_Qass"
    watch_folder(folder_to_watch)
