import tkinter as tk
from tkinter import messagebox, scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os
import glob


class FileHandler(FileSystemEventHandler):
    def __init__(self, app_textbox, teile_count_box, last_5_lines, folder_to_watch, root):
        self.count = 0
        self.app_textbox = app_textbox
        self.teile_count_box = teile_count_box
        self.last_5_lines = last_5_lines
        self.entnahme_frequenz = 1
        self.folder = folder_to_watch
        self.root = root

    def on_created(self, event):
        """Aktion, wenn eine Datei erstellt wird."""
        if event.is_directory:
            return
        self.count += 1
        self.teile_count_box.config(text=f"Anzahl Teile bis zur \n nächsten Entnahme: \n{self.entnahme_frequenz - (self.count % self.entnahme_frequenz)}")
        if self.count % self.entnahme_frequenz == 0:
            self.show_message(event)

    def show_message(self, event):
        """Zeigt eine Nachricht an."""
        def create_dialog():
            top = tk.Toplevel(self.root)
            top.attributes('-topmost', True)
            top.withdraw()
            response = messagebox.askokcancel("Meldung", "Bitte das Teil herausnehmen! Nach Herausnahme OK drücken.", parent=top)
            if response:
                self.handle_file(event)
        self.root.after(0, create_dialog)

    def handle_file(self, event=None):
        """Verarbeitet die Datei."""
        start_time = time.time()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        list_of_files = sorted(glob.glob(self.folder + "/*"))
        last_file = list_of_files[-1]
        needed_file = last_file

        if os.path.getctime(last_file) > start_time:
            needed_file = list_of_files[-2]
        qass_nr = needed_file.split("0025p")[1].split("c0b01")[0]
        self.save_to_file(current_time, qass_nr)
        self.update_textbox(qass_nr + " wurde herausgenommen. \n")

    def save_to_file(self, current_time, qass_nr):
        """Speichert Informationen in der Datei."""
        txt_path = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/DoE_Oli_TXT_fuer_Messungen/last_added_file.txt"
        with open(txt_path, 'a+') as file:
            file.write(current_time + ";" + qass_nr + "\n")
        with open(txt_path, 'r') as file:
            lines = file.readlines()
        if lines:
            last_5 = lines[-5:]
            formatted_text = '\n'.join([line.split(';')[1].strip() for line in last_5])
            self.last_5_lines.config(text=formatted_text)

    def update_textbox(self, message):
        """Aktualisiert die Textbox."""
        self.app_textbox.insert(tk.END, message)
        self.app_textbox.see(tk.END)

    def manual_removal(self):
        """Führt eine manuelle Entnahme durch."""
        self.handle_file()

    def delete_last_line(self):
        """Löscht die letzte Zeile und aktualisiert die Anzeige."""
        txt_path = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/DoE_Oli_TXT_fuer_Messungen/last_added_file.txt"
        lines = []
        with open(txt_path, 'r') as file:
            lines = file.readlines()
        if lines:
            last_line = lines[-1]
            qass_nr = last_line.split(";")[1].strip()
            with open(txt_path, 'w') as file:
                file.writelines(lines[:-1])
            self.update_textbox(qass_nr + " wurde gelöscht.")
        last_5 = lines[-5:-1]
        formatted_text = '\n'.join([line.split(';')[1].strip() for line in last_5])
        self.last_5_lines.config(text=formatted_text)


def watch_folder(folder_to_watch):
    """Beobachtet den angegebenen Ordner und zeigt die GUI an."""
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.title("Ordnerüberwachung")
    root.geometry("600x300+10+10")

    label1 = tk.Label(root, width=20, height=15, anchor='nw', justify='right', bg='white', relief='sunken')
    label1.pack(side=tk.RIGHT, padx=30, pady=10, fill=tk.BOTH, expand=True)
    app_textbox = scrolledtext.ScrolledText(label1, width=20, height=15)
    app_textbox.pack(side=tk.RIGHT, padx=0, pady=0)
    teile_counter = tk.Label(label1, text="Anzahl Teile bis zur \n nächsten Entnahme: \n 40", width=20, height=4, relief='flat')
    teile_counter.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
    überschrift_last5 = tk.Label(label1, text="\n \n Die 5 letzten \nherausgenommenen Teile:", width=20, height=4, anchor='nw', bg='white', relief='flat')
    überschrift_last5.pack(padx=20, pady=0, expand=False)
    last_5_lines = tk.Label(label1, width=20, height=20, bg='white', relief='sunken')
    last_5_lines.pack(padx=10, pady=10, expand=True)
    frame = tk.Frame(root)
    frame.pack(side=tk.RIGHT, padx=10, pady=10)

    event_handler = FileHandler(app_textbox, teile_counter, last_5_lines, folder_to_watch, root)

    # Binden der Funktionen an die Schaltflächen
    tk.Button(frame, text="Manuelle Entnahme", command=event_handler.manual_removal).pack(pady=10)
    tk.Button(frame, text="Zeile löschen", command=event_handler.delete_last_line, fg="red").pack(pady=10)

    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    folder_to_watch = "//sftpgwessbachsa.file.core.windows.net/sftpgwessbachfs/DoE_Verschleiss_Qass"
    watch_folder(folder_to_watch)
