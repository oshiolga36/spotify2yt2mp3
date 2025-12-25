import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import yt_dlp
import subprocess
import threading
import json
import os
import platform

CONFIG_FILE = "settings.json"


def save_settings(folder):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"last_folder": folder}, f)


def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("last_folder", "")
    return ""


def open_folder(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class Logger:
    def __init__(self, text_widget, status_label):
        self.text_widget = text_widget
        self.status_label = status_label

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        # Einfache Filterung für Status-Updates
        if "Downloading" in message and "[" not in message:
            clean_msg = message.replace("Downloading", "").strip()
            if clean_msg:
                self.status_label.config(text=f"Aktuell: {clean_msg}")

    def flush(self):
        pass


def download_logic(url, base_path, log_widget, progress_var, status_label):
    save_settings(base_path)
    import sys
    sys.stdout = Logger(log_widget, status_label)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    final_path = base_path  # Standardwert

    if "spotify.com" in url:
        status_label.config(text="Suche Spotify-Metadaten...")
        # spotdl --output sorgt hier für Unterordner pro Playlist/Album
        # Wir nutzen {list-title}/{title}.{ext} für Spotify
        cmd = ['spotdl', 'download', url, '--output', f"{base_path}/{{list-title}}/{{title}}.{{ext}}"]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                                   env=env, shell=True)
        for line in process.stdout:
            print(line, end='')
            if "Fetching" in line or "Downloading" in line:
                status_label.config(text=line.strip())
        process.wait()
    else:
        status_label.config(text="Analysiere YouTube Playlist...")
        # ydl_opts so anpassen, dass %(playlist_title)s ein Unterordner wird
        ydl_opts = {
            'outtmpl': f'{base_path}/%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s',
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Wir holen uns vorab den Titel für die finale Pfadanzeige
            try:
                info = ydl.extract_info(url, download=False)
                playlist_title = info.get('title', 'Unbekannte Playlist')
                final_path = os.path.join(base_path, playlist_title).replace("\\", "/")
            except:
                pass

            ydl.download([url])

    status_label.config(text="FERTIG! Alles im Playlist-Ordner gespeichert.")
    progress_var.set(100)

    # Ordner öffnen (wenn möglich den spezifischen Unterordner)
    if os.path.exists(final_path):
        open_folder(final_path)
    else:
        open_folder(base_path)


def start_thread():
    url = url_entry.get().strip()
    folder = folder_entry.get().strip()
    if not url or url == "Link hier einfügen..." or not folder:
        messagebox.showwarning("Fehler", "Link oder Ordner fehlt!")
        return

    status_label.config(text="Initialisiere...")
    progress_var.set(0)
    threading.Thread(target=download_logic, args=(url, folder, log_display, progress_var, status_label),
                     daemon=True).start()


def select_folder():
    path = filedialog.askdirectory()
    if path:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, path)


# --- GUI ---
root = tk.Tk()
root.title("Plex-Automator Downloader")
root.geometry("650x700")
root.configure(bg="#121212")

style = ttk.Style()
style.theme_use('clam')
style.configure("TProgressbar", thickness=15, background="#1DB954")

tk.Label(root, text="Auto-Playlist Downloader", fg="#1DB954", bg="#121212", font=("Helvetica", 18, "bold")).pack(
    pady=20)

url_entry = tk.Entry(root, width=60, bg="#282828", fg="white", insertbackground="white", font=("Arial", 10))
url_entry.insert(0, "Link hier einfügen...")
url_entry.pack(pady=10)

tk.Label(root, text="Basis-Verzeichnis (z.B. Plex Musik Ordner):", fg="#b3b3b3", bg="#121212",
         font=("Helvetica", 9)).pack()
folder_frame = tk.Frame(root, bg="#121212")
folder_frame.pack(pady=5)
folder_entry = tk.Entry(folder_frame, width=45, bg="#282828", fg="white", insertbackground="white")
folder_entry.insert(0, load_settings())
folder_entry.pack(side=tk.LEFT, padx=5)
tk.Button(folder_frame, text="Pfad wählen", command=select_folder, bg="#535353", fg="white").pack(side=tk.LEFT)

tk.Button(root, text="DOWNLOAD STARTEN", command=start_thread, bg="#1DB954", fg="black", font=("Helvetica", 12, "bold"),
          width=25).pack(pady=20)

status_label = tk.Label(root, text="Bereit", fg="#b3b3b3", bg="#121212", font=("Helvetica", 10, "italic"))
status_label.pack(pady=5)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=500, mode='determinate',
                               style="TProgressbar")
progress_bar.pack(pady=5)

log_display = scrolledtext.ScrolledText(root, height=12, width=80, bg="#191414", fg="#00FF00", font=("Consolas", 8))
log_display.pack(pady=15)

root.mainloop()
