import inspect
import json
import os
import threading
import time
import zipfile

import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk
import tkinterdnd2

import mido
import mido.backends.rtmidi


class Midi_Player:
    def __init__(self):
        self.is_playing = False
        self.current_time = 0
        self.midi = None
        ports = mido.get_output_names()
        self.outport = mido.open_output(ports[0])

    def reset_time(self):
        self.current_time = 0
        label_sequencer["text"] = "0:0"
        canvas.moveto("sequencer_line", 0, 0)
        canvas.xview_moveto(0)

    def stop(self):
        self.is_playing = False
        self.outport.reset()

    def play(self):
        def midi_play():
            midi_file = self.midi

            messages = []
            sum_time = 0
            bpm = 1000000
            for msg in midi_file:
                if msg.type == "set_tempo":
                    bpm = msg.tempo
                sum_time += msg.time * midi_file.ticks_per_beat * 1000 * 1000 / bpm
                if sum_time >= self.current_time:
                    messages.append(msg)

            if len(messages) > 0:
                i = 0
                while i < len(messages) - 1 and self.is_playing:
                    msg = messages[i]
                    if msg.type == "set_tempo":
                        label_bpm["text"] = "bpm:" + str(int(mido.tempo2bpm(msg.tempo)))
                        label_bpm.update()
                    if not msg.is_meta:
                        self.outport.send(msg)
                    time.sleep(messages[i + 1].time)
                    i += 1

                self.outport.send(messages[-1])

            self.stop()

        if self.midi is None:
            addlog("midiが読み込まれてないのだ")
            return

        if self.is_playing:
            self.stop()
            return

        self.is_playing = True

        thread_play = threading.Thread(target=midi_play)
        thread_play.start()


class Com_file:
    def __init__(self, data):
        self.data = data
        self.midi = None
        self.com_changed = True

    def save(self):
        file_path = self.data["path"]
        if file_path is None:
            file_path = filedialog.asksaveasfilename(filetypes=[("Com", ".cmcm")])
            self.data["path"] = file_path

        if len(file_path) == 0:
            addlog("canceled")
            return

        if get_file_extension(file_path) != "cmcm":
            file_path += ".cmcm"

        if not os.path.exists("./temp"):
            os.makedirs("./temp")

        with open("./temp/temp.json", "wt") as f:
            json.dump(self.data, f)

        with zipfile.ZipFile(
            file_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            zf.write("./temp/temp.json")

        os.remove("./temp/temp.json")

        addlog(".comcomを保存したのだ")

    def write(self):
        file_path = filedialog.asksaveasfilename(filetypes=[("MIDI", ".mid")])
        if len(file_path) == 0:
            return

        if get_file_extension(file_path) != "mid":
            file_path += ".mid"
        self.get_midi().save(file_path)
        addlog("midiファイルを作成したのだ")

    def get_midi(self):
        if self.com_changed or self.midi is None:
            self.midi = self.make_midi()
            self.com_changed = False

        return self.midi

    def make_midi(self):
        addlog("comcomをmidiに変換開始")
        midi_file = mido.MidiFile(type=1)

        midi_file.ticks_per_beat = 480

        for track in self.data["tracks"]:
            midi_track = mido.MidiTrack()
            midi_file.tracks.append(midi_track)

            channel = track["channel"]

            # 重なり検出
            notes = resolve_overlapping(track["notes"])

            note_massages = []
            for note in notes:
                note_massages.append(
                    {
                        "type": "note_on",
                        "note": note["pitch"],
                        "velocity": note["velocity"] or 127,
                        "tick": note["tick"],
                    }
                )
                note_massages.append(
                    {
                        "type": "note_off",
                        "note": note["pitch"],
                        "tick": note["tick"] + note["length"],
                    }
                )

            event_messages = [*track["events"]]

            event_messages.append(
                {"type": "track_name", "name": track["track_name"], "tick": 0}
            )

            messages = sorted(track["events"] + note_massages, key=lambda x: x["tick"])

            current_time = 0
            for message in messages:
                neo_message = {**message}
                neo_message["time"] = neo_message["tick"] - current_time
                current_time = neo_message["tick"]
                neo_message.pop("tick")

                try:
                    m = mido.Message.from_dict(neo_message)
                except:
                    m = mido.MetaMessage.from_dict(neo_message)

                if hasattr(m, "channel"):
                    m.channel = channel

                midi_track.append(m)

        addlog("変換が終了したのだ")

        temp_path = "./temp/temp.mid"

        if not os.path.exists("./temp"):
            os.makedirs("./temp")
        with open(temp_path, "wt"):
            midi_file.save(temp_path)
        midi_file = mido.MidiFile(temp_path)

        os.remove(temp_path)

        return midi_file


def resolve_overlapping(notes):
    super_notes = []
    for note in notes:
        overlapping_notes_index = [
            index
            for index in range(len(super_notes))
            if super_notes[index]["pitch"] == note["pitch"]
            and super_notes[index]["tick"]
            <= note["tick"]
            < super_notes[index]["tick"] + super_notes[index]["length"]
        ]

        flag = False
        for j in overlapping_notes_index:
            o_note = super_notes[j]
            if o_note["tick"] == note["tick"]:
                flag = True
                break
            else:
                o_note["length"] = note["tick"] - o_note["tick"]

        if flag:
            continue

        super_notes.append(note)
    return super_notes


# ファイルをドロップする
def on_drop_file(event):
    keys = can_drop_file.keys()
    path = event.data.strip("}").strip("{")

    ex = get_file_extension(path)

    if ex in keys:
        can_drop_file[ex](path)

    else:
        addlog("これは" + ex + "なのだ、読み込み登録されてないのだ")


# logに表示+print
def addlog(text):
    print(text)
    log["state"] = "normal"
    log.insert(tk.END, text + "\n")
    log["state"] = "disabled"
    log.see("end")
    log.update()


one_printed = False


def one_print(t):
    global one_printed
    if not one_printed:
        print(t)
        one_printed = True


terminal_row = 0


# 呼び出し位置を確認できる、lineで位置を指定して上書きする
# 使い始める前にresetをTrueにする
def debug(text="", line=0, reset=False):
    global terminal_row
    if reset:
        terminal_row = 0
        return None

    print("\n" * line)

    output = (
        "file: "
        + str(os.path.basename(inspect.currentframe().f_back.f_code.co_filename))
        + ", line: "
        + str(inspect.currentframe().f_back.f_lineno)
        + ", "
        + text
    )

    print(
        "\033[" + str(terminal_row + 1) + "A\r",
        output + "-" * (100 - len(output)),
        end="",
    )
    terminal_row = line


# 拡張子を得る
def get_file_extension(file_path):
    if "." in file_path:
        p = os.path.splitext(file_path)[1][1:]
        return p
    else:
        return None


# ----------------------------------------------------------
def get_mark(x):
    if len(com_files) == 0:
        return
    com = com_files[com_select]

    start = com.data["start"]

    mlt = 480 / com.data["beat_length"]

    x = x * mlt - start

    marks = [240 * i for i in range(int(x / 240) + 2)]
    x = min(marks, key=lambda m: (m - x) ** 2)

    return x


def on_click_canvas(event):
    if len(com_files) == 0:
        return
    com = com_files[com_select]

    start = com.data["start"]

    mlt = 480 / com.data["beat_length"]

    x = get_mark(canvas.canvasx(event.x))
    label_sequencer["text"] = str(int(x / 1920)) + ":" + str(x % 1920)
    midi_player.current_time = x + start

    canvas.moveto("sequencer_line", (x + start) / mlt - 2, 0)
    canvas.lift("sequencer_line")


def on_move_on_canvas(event):
    x = get_mark(canvas.canvasx(event.x))
    y = 127 - int(canvas.canvasy(event.y) / 8)

    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    label = notes[y % 12] + str(int(y / 12) - 1) + "=" + str(y)

    label += "\n" + str(int(x / 1920)) + ":" + str(x % 1920)

    label_coordinate["text"] = label


def on_button_play():
    if midi_player.is_playing:
        button_play["text"] = "▶"
        midi_player.stop()
    else:
        com_file = com_files[com_select]
        midi_player.midi = com_file.get_midi()

        button_play["text"] = "■"
        midi_player.play()


def get_com_from_path(path):
    if not os.path.exists("./temp"):
        os.makedirs("./temp")

    with zipfile.ZipFile(path) as zf:
        zf.extractall("./")

    with open("./temp/temp.json", "r") as f:
        C = Com_file(json.load(f))

    os.remove("./temp/temp.json")

    read_com(C)


def read_com(com_file: Com_file):
    global com_select

    com_files.append(com_file)

    com_select = len(com_files) - 1

    midi_player.stop()

    load_com()

    draw_all_notes()

    addlog("cmcmファイルを読み込んだのだ")


def load_com():
    if len(com_files) == 0:
        return

    com = com_files[com_select]
    names = [com.data["name"] or "NoTitle" for com in com_files]

    combobox_com["value"] = names
    combobox_com.set(names[com_select])

    names = []
    for i, track in enumerate(com.data["tracks"]):
        name = track["track_name"] or "NoName"
        names.append(f"{i}: " + name)

    t = com.data["selected_track"]

    combobox_track["values"] = names
    combobox_track.set(combobox_track["values"][t])

    update_log_message(t)
    draw_all_notes()


def read_midi_file(file_path: str):
    addlog("MIDIデータ読み込み開始...")

    try:
        midi_file = mido.MidiFile(file_path)
    except:
        addlog("読み込めないみたいなのだ!")
        return

    C = Com_file(translate_midi_file(midi_file, os.path.basename(file_path)))

    read_com(C)

    addlog(os.path.basename(file_path) + "を読み込んだのだ")


# midiファイルを読み込み、描画用の形式に変換する
def translate_midi_file(midi_file: mido.MidiFile, name: str):
    if midi_player.is_playing:
        midi_player.stop()

    channel_error = False

    com = {
        "tracks": [],
        "beat_length": 20,
        "format": 0,
        "length": 0,
        "name": name,
        "path": None,
        "start": float("inf"),
    }

    mlt = int(480 / midi_file.ticks_per_beat)

    # 扱いやすい形に変換
    for track in midi_file.tracks:
        tra = {
            "channel": None,
            "length": 0,
            "track_name": "NoName",
            "events": [],
            "notes": [],
        }

        time = 0  # ノートの絶対時刻
        start = None

        for message in track:
            message.time *= mlt

            time += message.time

            if hasattr(message, "channel"):
                if tra["channel"] is None:
                    tra["channel"] = message.channel
                elif tra["channel"] != message.channel and not channel_error:
                    addlog("1トラックに異なるチャネルが混じっております!")
                    addlog("とりあえず無理やり読み込んでみますが元データとちょっと異なっちゃうかもです!")
                    channel_error = True

            # on命令
            if message.type == "note_on":
                if start == None:
                    start = time

                tra["notes"].append(
                    {
                        "pitch": message.note,
                        "length": None,
                        "velocity": message.velocity,
                        "tick": time,
                    }
                )

            # off命令
            elif message.type == "note_off":
                # 後ろから探索して音程が同じかつまだ長さが設定されていないものを探す
                for note in tra["notes"][::-1]:
                    if note["pitch"] == message.note and note["length"] is None:
                        note["length"] = time - note["tick"]
                        break

            else:
                # track_nameはcomが管理する。midi書き出し時に再び追加する
                if message.type == "track_name":
                    tra["track_name"] = message.name
                    continue

                e = message.dict()
                e["tick"] = time
                e.pop("time")
                tra["events"].append(e)

        if start is not None:
            com["start"] = min(com["start"], start)

        tra["length"] = time

        com["tracks"].append(tra)

    com["length"] = max(track["length"] for track in com["tracks"])
    com["selected_track"] = 0

    midi_player.current_time = 0

    return com


def menu_select_cmcm():
    file_path = filedialog.askopenfilename(filetypes=[("cmcm", ".cmcm")])

    if len(file_path) == 0:
        addlog("cmcmが選択されなかったのだ")
        return None

    if get_file_extension(file_path) != "cmcm":
        addlog("cmcmファイルを選択して、なのだ")
        return None

    get_com_from_path(file_path)


# midiファイルを選択する
def menu_select_midi():
    file_path = filedialog.askopenfilename(filetypes=[("midi", ".mid")])

    if len(file_path) == 0:
        addlog("MIDIが選択されなかったのだ")
        return None

    if get_file_extension(file_path) != ("mid" or "midi"):
        addlog("MIDIファイルを選択して、なのだ")
        return None

    read_midi_file(file_path)


def draw_all_notes():
    if len(com_files) == 0:
        addlog("cmcmが選択されていないのだ")
        return

    com_file = com_files[com_select]

    # キャンバスをクリア
    canvas.delete("all")

    beat = com_file.data["beat_length"]

    mlt = beat / 480

    length = com_file.data["length"] * mlt + 4 * beat

    scale = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]

    # 白鍵黒鍵
    for y in range(128):
        colour = "#ddddff"
        if scale[(y + 9) % 12] == 0:
            colour = "#ffffff"

        canvas.create_rectangle(0, y * 8, length, (y + 1) * 8, fill=colour)
    off_set_x = com_file.data["start"]

    # C
    for y in range(int(128 / 12)):
        canvas.create_line(
            0,
            (y * 12 + 8) * 8,
            length,
            (y * 12 + 8) * 8,
            fill="#000000",
            width=2,
        )

    # 小節
    for x in range(int(com_file.data["length"] / 1920) + 1):
        canvas.create_line(
            x * 4 * beat + off_set_x * mlt,
            0,
            x * 4 * beat + off_set_x * mlt,
            canvas["height"] * 3,
            fill="#636363",
        )

    for t in range(len(com_file.data["tracks"])):
        draw_notes(t, "#aaaaaa")

    draw_notes(com_file.data["selected_track"], "#7777ff")

    canvas.create_line(0, 0, 0, 8 * 128, fill="#000000", width=2, tags="sequencer_line")
    canvas.lift("sequencer_line")

    canvas.config(scrollregion=(0, 0, length, int(8 * 129.5)))


def draw_notes(track_num: int, colour: str):
    if len(com_files) == 0:
        addlog("cmcmが選択されていないのだ")
        return

    com_file = com_files[com_select]

    mlt = com_file.data["beat_length"] / 480

    t = com_file.data

    # ノートの描画
    for note in t["tracks"][track_num]["notes"]:
        if note["length"] is not None:
            # ノートの長さを計算
            x1 = note["tick"] * mlt
            x2 = x1 + note["length"] * mlt
            y1 = (127 - note["pitch"]) * 8
            y2 = y1 + 8

            if com_file.data["tracks"][track_num]["channel"] == 9:
                canvas.create_oval(
                    x1 - 4, y1, x1 + 4, y2, fill=colour, tags=f"track:{track_num}"
                )
            else:
                canvas.create_rectangle(
                    x1, y1, x2, y2, fill=colour, tags=f"track:{track_num}"
                )


def on_select_track(event):
    t = event.widget.current()
    update_log_message(t)
    addlog(str(t) + "番にトラックを変更したのだ")


def update_log_message(t):
    if len(com_files) == 0:
        return
    com_file = com_files[com_select]

    canvas.itemconfig(f"track:{com_file.data['selected_track']}", fill="#aaaaaa")
    com_file.data["selected_track"] = t
    canvas.itemconfig(f"track:{t}", fill="#7777ff")
    canvas.lift(f"track:{t}")

    tra = com_file.data["tracks"][t]

    log_notes.delete(0, "end")
    for msg in tra["notes"]:
        log_notes.insert(tk.END, str(msg) + "\n")

    log_events.delete(0, "end")
    for msg in tra["events"]:
        log_events.insert(tk.END, str(msg) + "\n")

    log_notes.update()
    log_events.update()


def on_select_com_file(event):
    global com_select
    c = event.widget.current()
    if com_select != c:
        com_select = c
        draw_all_notes()
        midi_player.stop()
        update_log_message(com_files[com_select].data["selected_track"])
        load_com()


def on_key_action(event):
    print(event.keysym)

    if event.keysym in key_listener.keys():
        key_listener[event.keysym]()


def on_window_closed():
    addlog("終了処理を開始するのだ...")
    midi_player.stop()
    for p in processes:
        p.kill()
    root.destroy()


def menu_save_cmcm():
    if len(com_files) == 0:
        addlog("comないのだ")
    else:
        com_files[com_select].save()


def menu_write_to_midi():
    if len(com_files) == 0:
        addlog("comないのだ")
    else:
        com_files[com_select].write()


def on_button_zoom(key):
    if len(com_files) == 0:
        return

    com = com_files[com_select]

    if key == "reset":
        com.data["beat_length"] = 20
    elif key == "+":
        com.data["beat_length"] *= 2
    elif key == "-":
        com.data["beat_length"] /= 2

    com.changed_com = True

    draw_all_notes()


# ---------------------------------------------------------------------------


# can_drop_file = {"ex": function}
can_drop_file = {}
can_drop_file["mid"] = read_midi_file
can_drop_file["cmcm"] = get_com_from_path

com_files = []
com_select = 0

midi_player = Midi_Player()

# listeners = {"key": function}
key_listener = {}
key_listener["space"] = on_button_play

midi_file = None

processes = []


# ----------------------------------------------------------

root = tkinterdnd2.Tk()
root.title("AIこんぽ～ざ～")
root.geometry("960x320")
root.bind("<Key>", on_key_action)
root.protocol("WM_DELETE_WINDOW", on_window_closed)

menubar = tk.Menu(root)
root.config(menu=menubar)

file = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="File", menu=file)

edit = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Edit", menu=edit)

exe = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="exe", menu=exe)


file.add_command(label="open_cmcm...", command=menu_select_cmcm)
file.add_command(label="open_midi...", command=menu_select_midi)
file.add_command(label="save_cmcm...", command=menu_save_cmcm)
file.add_command(label="write_to_midi...", command=menu_write_to_midi)

edit.add_command(label="reload", command=load_com)

# --------------------------------------------------------------------------

root.columnconfigure(0, weight=0)
root.columnconfigure(1, weight=1)
root.rowconfigure(0, weight=1)

frame_green = tk.Frame(root, width=360, height=540)
frame_green.propagate(False)
frame_green.grid(row=0, column=0, sticky="nsew")

frame_black = tk.Frame(root, width=600, height=540, bg="black")
frame_black.propagate(False)
frame_black.grid(row=0, column=1, sticky="nsew")

frame_yellow = tk.Frame(frame_green, width=360, height=40, bg="yellow")
frame_yellow.propagate(False)
frame_yellow.grid(row=0, column=0)

label_track = tk.Label(frame_yellow, width=6, height=4, text="Track:")
label_track.pack(side="left")

combobox_track = ttk.Combobox(frame_yellow, values=[0], state="readonly")
combobox_track.set(0)
combobox_track.bind("<<ComboboxSelected>>", on_select_track)
combobox_track.pack(side="left", fill="both", expand=True)

button_play = tk.Button(
    frame_yellow, width=6, height=4, text="▶", command=on_button_play
)
button_play.pack(side="right")

button_reset = tk.Button(
    frame_yellow, width=6, height=4, text="◀", command=midi_player.reset_time
)
button_reset.pack(side="right")

frame_green.rowconfigure(0, weight=0)
frame_green.rowconfigure(1, weight=1)

notebook_left = ttk.Notebook(frame_green)
notebook_left.grid(row=1, column=0, sticky="nsew")


log = tk.Text(notebook_left, width=36, state="disabled")
log.pack(fill="both")
scroll_log = tk.Scrollbar(log, orient=tk.VERTICAL)
scroll_log.config(command=log.yview)
log.config(yscrollcommand=scroll_log.set)
scroll_log.pack(side="right", fill="y")

log_notes = tk.Listbox(notebook_left, width=36)
log_notes.pack(fill="both")
scroll_log_notes = tk.Scrollbar(log_notes, orient=tk.VERTICAL)
scroll_log_notes.config(command=log_notes.yview)
log_notes.config(yscrollcommand=scroll_log_notes.set)
scroll_log_notes.pack(side="right", fill="y")

log_events = tk.Listbox(notebook_left, width=36)
log_events.pack(fill="both")
scroll_log_events = tk.Scrollbar(log_events, orient=tk.VERTICAL)
scroll_log_events.config(command=log_events.yview)
log_events.config(yscrollcommand=scroll_log_events.set)
scroll_log_events.pack(side="right", fill="y")

notebook_left.add(log, text="LOG")
notebook_left.add(log_notes, text="NOTES")
notebook_left.add(log_events, text="EVENTS")

# ---------------------------------------------------------------------------

frame_black.columnconfigure(0, weight=1)

frame_black.rowconfigure(0, weight=0)
frame_black.rowconfigure(1, weight=1)

frame_red = tk.Frame(frame_black, width=600, height=40)
frame_red.propagate(False)
frame_red.grid(row=0, column=0, sticky="we")

canvas = tk.Canvas(frame_black, width=600, height=500, bg="#151515")
canvas.grid(row=1, column=0, sticky="nswe")

# Scrollbarを生成してCanvasに配置処理
scroll_y_canvas = tk.Scrollbar(canvas, orient=tk.VERTICAL)
scroll_x_canvas = tk.Scrollbar(canvas, orient=tk.HORIZONTAL)
scroll_y_canvas.pack(side=tk.RIGHT, fill=tk.Y)
scroll_x_canvas.pack(side=tk.BOTTOM, fill=tk.X)
scroll_y_canvas.config(command=canvas.yview)
scroll_x_canvas.config(command=canvas.xview)
canvas.config(yscrollcommand=scroll_y_canvas.set, xscrollcommand=scroll_x_canvas.set)
canvas.config(scrollregion=(0, 0, 480, 640))  # Canvasのスクロール範囲を設定

canvas.drop_target_register(tkinterdnd2.DND_FILES)
canvas.dnd_bind("<<Drop>>", on_drop_file)

canvas.bind("<Button-1>", on_click_canvas)
canvas.bind("<Motion>", on_move_on_canvas)

combobox_com = ttk.Combobox(frame_red, height=40, values=[0], state="readonly")
combobox_com.set(0)
combobox_com.bind("<<ComboboxSelected>>", on_select_com_file)
combobox_com.pack(side="right", fill="y")

label_coordinate = tk.Label(frame_red, width=6, text="C-1=0\n0:0")
label_coordinate.pack(side="right")

label_sequencer = tk.Label(frame_red, width=6, text="0:0")
label_sequencer.pack(side="right")

label_bpm = tk.Label(frame_red, width=6, text="bgm:120")
label_bpm.pack(side="right")

button_zoom0 = tk.Button(
    frame_red,
    width=4,
    height=40,
    text="reset\nzoom",
    command=lambda: on_button_zoom("reset"),
)
button_zoom1 = tk.Button(
    frame_red,
    width=4,
    height=40,
    text="-",
    font=("normal", 16),
    command=lambda: on_button_zoom("-"),
)
button_zoom2 = tk.Button(
    frame_red,
    width=4,
    height=40,
    text="+",
    font=("normal", 16),
    command=lambda: on_button_zoom("+"),
)
button_zoom0.pack(side="left")
button_zoom2.pack(side="left")
button_zoom1.pack(side="left")

# # ---------------------------------------------------------------------------

default_path = "./d.cmcm"

if os.path.exists(default_path):
    with open(default_path, "r") as f:
        get_com_from_path(default_path)
