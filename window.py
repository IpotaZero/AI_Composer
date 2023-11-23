import inspect
import json
import os
import threading
import time

import tkinter as tk
import tkinter.ttk
import tkinterdnd2

import mido
import mido.backends.rtmidi


class Midi_Player:
    def __init__(self):
        self.is_playing = False
        self.current_time = 0
        self.midi = None
        self.tempo = 120
        ports = mido.get_output_names()
        self.outport = mido.open_output(ports[0])

    def reset_time(self):
        self.current_time = 0
        label1["text"] = 0
        canvas.moveto("sequencer_line", 0, 0)

    def stop(self):
        self.is_playing = False
        button_play["text"] = "▶"

        for i in range(128):
            self.outport.send(mido.Message(type="note_off", note=i, time=0))
        addlog("再生を終了したのだ")

    def play(self):
        def midi_play():
            midi_file = self.midi

            current_position = (
                self.current_time
                * self.tempo
                / (midi_file.ticks_per_beat * 1000 * 1000)
            )

            messages = []
            sum_time = 0
            for msg in midi_file:
                sum_time += msg.time
                if sum_time >= current_position:
                    messages.append(msg)

            if len(messages) > 0:
                i = 0
                while i < len(messages) - 1 and self.is_playing:
                    msg = messages[i]
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

        addlog("再生を開始するのだ")

        self.is_playing = True

        thread_play = threading.Thread(target=midi_play)
        thread_play.start()


class Com_file:
    def __init__(self):
        self.data = None
        self.midi = None
        self.com_changed = True

    def save(self):
        file_path = self.data["path"]
        if file_path is None:
            file_path = tk.filedialog.asksaveasfilename(filetypes=[("Com", ".comcom")])
            self.data["path"] = file_path

        if len(file_path) == 0:
            addlog("canceled")
            return

        with open(file_path, "wt") as f:
            json.dump(self.data, f)

        addlog(".comcomを保存したのだ")

    def load(self, path):
        with open(path, "r") as f:
            self.data = json.load(f)

    def write(self):
        file_path = tk.filedialog.asksaveasfilename(filetypes=[("MIDI", ".mid")])
        if len(file_path) == 0:
            return
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

            note_massages = []
            for note in track["notes"]:
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

            messages = sorted(track["events"] + note_massages, key=lambda x: x["tick"])

            current_time = 0
            for message in messages:
                neo_message = {**message}
                neo_message["time"] = neo_message["tick"] - current_time
                current_time = neo_message["tick"]
                neo_message.pop("tick")

                try:
                    m = mido.Message(**neo_message)
                except:
                    m = mido.MetaMessage(**neo_message)

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


# ファイルをドロップする
def drop_file(event):
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
def click_canvas(event):
    x = canvas.canvasx(int(event.x)) * 24
    x = x - x % 120
    label1["text"] = x
    midi_player.current_time = x

    canvas.moveto("sequencer_line", canvas.canvasx(int(event.x)), 0)
    canvas.lift("sequencer_line")


def play():
    com_file = com_files[com_select]
    midi_player.midi = com_file.get_midi()
    midi_player.tempo = com_file.data["tempo"]

    button_play["text"] = "■"
    midi_player.play()


def get_com_from_path(path):
    C = Com_file()

    with open(path, "r") as f:
        C.data = json.load(f)

    read_com(C)


def read_com(com_file: Com_file):
    global com_select

    com_files.append(com_file)

    print(com_files)

    names = [com.data["name"] for com in com_files]

    combobox_com["value"] = names
    com_select = len(com_files) - 1
    combobox_com.set(names[com_select])

    combobox0["values"] = list(range(len(com_file.data["tracks"])))
    combobox0.set(0)

    draw_all_notes()

    addlog("comcomファイルを読み込んだのだ")


def read_midi_file(file_path: str):
    addlog("MIDIデータ読み込み開始...")

    try:
        midi_file = mido.MidiFile(file_path)
    except:
        addlog("読み込めないみたいなのだ!")
        return

    C = Com_file()
    C.data = translate_midi_file(midi_file, os.path.basename(file_path))

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
        "tempo": 0,
    }

    mlt = int(480 / midi_file.ticks_per_beat)

    # 扱いやすい形に変換
    for track in midi_file.tracks:
        tra = {
            "channel": None,
            "length": 0,
            "track_name": None,
            "events": [],
            "notes": [],
        }

        time = 0  # ノートの絶対時刻

        for message in track:
            message.time *= mlt

            time += message.time
            start = None

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
                        "tick": time,
                        "length": None,
                        "velocity": message.velocity,
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
                if message.type == "set_tempo":
                    com["tempo"] = message.tempo
                if message.type == "track_name":
                    tra["track_name"] = message.name

                e = vars(message)
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


# midiファイルを選択する
def click_fileselect():
    file_path = tk.filedialog.askopenfilename(filetypes=[("midi", ".mid")])

    if len(file_path) == 0:
        addlog("MIDIが選択されなかったのだ")
        return None

    if get_file_extension(file_path) != ("mid" or "midi"):
        addlog("MIDIファイルを選択して、なのだ")
        return None

    read_midi_file(file_path)


def draw_all_notes():
    com_file = com_files[com_select]

    if com_file.data is None:
        addlog("MIDIが選択されていないのだ")
        return None

    # キャンバスをクリア
    canvas.delete("all")

    mlt = com_file.data["beat_length"] / 480

    scale = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]

    for y in range(128):
        colour = "#ddddff"
        if scale[(y + 9) % 12] == 0:
            colour = "#ffffff"

        canvas.create_rectangle(
            0, y * 8, com_file.data["length"] * mlt, (y + 1) * 8, fill=colour
        )
    off_set_x = com_file.data["start"]

    for y in range(int(128 / 12)):
        canvas.create_line(
            0,
            (y * 12 + 8) * 8,
            com_file.data["length"] * mlt,
            (y * 12 + 8) * 8,
            fill="#000000",
            width=2,
        )

    for x in range(int(com_file.data["length"] / 1920)):
        canvas.create_line(
            x * 80 + off_set_x * mlt,
            0,
            x * 80 + off_set_x * mlt,
            canvas["height"] * 3,
            fill="#636363",
        )

    for t in range(len(com_file.data["tracks"])):
        draw_notes(t, "#777777")

    draw_notes(com_file.data["selected_track"], "#5555ff")

    canvas.create_line(0, 0, 0, 8 * 128, fill="#000000", width=2, tags="sequencer_line")
    canvas.lift("sequencer_line")

    canvas.config(scrollregion=(0, 0, 480 + com_file.data["length"] * mlt, 8 * 128))


def draw_notes(track_num: int, colour: str):
    com_file = com_files[com_select]

    if com_file.data is None:
        addlog("MIDIが選択されていないのだ")
        return None

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
                    x1 - 4, y1, x2 + 4, y2, fill=colour, tags=f"track:{track_num}"
                )
            else:
                canvas.create_rectangle(
                    x1, y1, x2, y2, fill=colour, tags=f"track:{track_num}"
                )


def track_select(event):
    com_file = com_files[com_select]

    if com_file.data is not None:
        canvas.itemconfig(f"track:{com_file.data['selected_track']}", fill="#777777")

        com_file.data["selected_track"] = event.widget.current()
        # save(com_file.data)

        canvas.itemconfig(f"track:{com_file.data['selected_track']}", fill="#5555ff")

        addlog(str(event.widget.current()) + "番にトラックを変更したのだ")


def com_file_select(event):
    global com_select
    c = event.widget.current()
    if com_select != c:
        com_select = c
        draw_all_notes()
        midi_player.stop()


def key_action(event):
    print(event.keysym)

    if event.keysym in key_listener.keys():
        key_listener[event.keysym]()


def on_window_closed():
    addlog("終了処理を開始するのだ...")
    midi_player.stop()
    for p in processes:
        p.kill()
    root.destroy()


def save():
    if len(com_files) == 0:
        addlog("comないのだ")
    else:
        com_files[com_select].save()


def write():
    if len(com_files) == 0:
        addlog("comないのだ")
    else:
        com_files[com_select].write()


# ---------------------------------------------------------------------------


# can_drop_file = {"ex": function}
can_drop_file = {}
can_drop_file["mid"] = read_midi_file
can_drop_file["comcom"] = get_com_from_path

com_files = []
com_select = 0

midi_player = Midi_Player()

# listeners = {"key": function}
key_listener = {}
key_listener["space"] = play

midi_file = None

processes = []


# ----------------------------------------------------------

root = tkinterdnd2.Tk()
root.title("AIこんぽ～ざ～")
root.geometry("960x320")

root.bind("<Key>", key_action)

menubar = tk.Menu(root)
root.config(menu=menubar)

file = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="File", menu=file)

edit = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Edit", menu=edit)

exe = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="exe", menu=exe)

frame0 = tk.Frame(root, width=360)
frame0.pack(side="left", anchor="n", fill="y")

log = tk.Text(frame0, state="disabled")
log.place(x=0, y=20, width=360, relheight=1)
# Scrollbarを生成してCanvasに配置処理
scroll_log = tk.Scrollbar(log, orient=tk.VERTICAL)
scroll_log.pack(side=tk.RIGHT, fill=tk.Y)
scroll_log.config(command=log.yview)
log.config(yscrollcommand=scroll_log.set)

# ---------------------------------------------------------------------------

root.protocol("WM_DELETE_WINDOW", on_window_closed)

file.add_command(label="open_midi...", command=click_fileselect)
file.add_command(label="save_translated_midi", command=save)
file.add_command(label="write_to_midi", command=write)

# ---------------------------------------------------------------------------

label_track_num = tk.Label(frame0, text="Track_Num:")
label_track_num.place(x=0, y=0, width=80, height=20)

combobox0 = tk.ttk.Combobox(frame0, values=[0], state="readonly")
combobox0.set(0)
combobox0.bind("<<ComboboxSelected>>", track_select)
combobox0.place(x=80, y=0, width=120, height=20)

combobox_com = tk.ttk.Combobox(frame0, values=[0], state="readonly")
combobox_com.set(0)
combobox_com.bind("<<ComboboxSelected>>", com_file_select)
combobox_com.place(x=80, y=20, width=120, height=20)

button_play = tk.Button(frame0, text="▶", command=play)
button_play.place(x=240, y=0, width=20, height=20)

button_reset = tk.Button(frame0, text="◀", command=midi_player.reset_time)
button_reset.place(x=220, y=0, width=20, height=20)

label1 = tk.Label(frame0, text="0")
label1.place(x=260, y=0, width=100, height=20)

frame1 = tk.Frame(root)
frame1.pack(side="left", anchor="n", fill="both", expand=True)


canvas = tk.Canvas(frame1, bg="#151515")
canvas.pack(side="left", anchor="n", fill="both", expand=True)

# Scrollbarを生成してCanvasに配置処理
bar_y = tk.Scrollbar(canvas, orient=tk.VERTICAL)
bar_x = tk.Scrollbar(canvas, orient=tk.HORIZONTAL)
bar_y.pack(side=tk.RIGHT, fill=tk.Y)
bar_x.pack(side=tk.BOTTOM, fill=tk.X)
bar_y.config(command=canvas.yview)
bar_x.config(command=canvas.xview)
canvas.config(yscrollcommand=bar_y.set, xscrollcommand=bar_x.set)
# Canvasのスクロール範囲を設定
canvas.config(scrollregion=(0, 0, 480, 640))

canvas.drop_target_register(tkinterdnd2.DND_FILES)
canvas.dnd_bind("<<Drop>>", drop_file)

canvas.bind("<Button-1>", click_canvas)

default_path = "./d.comcom"

if os.path.exists(default_path):
    with open(default_path, "r") as f:
        C = Com_file()
        C.data = json.load(f)
        read_com(C)
