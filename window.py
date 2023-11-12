import importlib
import inspect
import json
import os
import threading
import time

import tkinter
import tkinter.ttk
import tkinterdnd2

import mido


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
    log.insert(tkinter.END, text + "\n")
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


def read_midi_file(file_path: str):
    global translated_midi_file, midi_file
    addlog("MIDIデータ読み込み開始...")

    midi_file = mido.MidiFile(file_path)

    translated_midi_file = translate_midi_file(midi_file, os.path.basename(file_path))

    combobox0["values"] = list(range(len(translated_midi_file["tracks"])))
    combobox0.set(0)

    draw_all_notes()
    addlog(os.path.basename(file_path) + "を読み込んだのだ")


# midiファイルを読み込み、描画用の形式に変換する
def translate_midi_file(midi_file: mido.MidiFile, name: str):
    if midi_player["is_playing"]:
        midi_stop()

    t = {
        "tracks": [],
        "length": 0,
        "name": name,
        "start": float("inf"),
        "tempo": 0,
        "resolusion": midi_file.ticks_per_beat,
    }

    mlt = int(480 / t["resolusion"])

    debug(reset=True)

    # 扱いやすい形に変換
    for i in range(len(midi_file.tracks)):
        track = midi_file.tracks[i]

        notes = []  # ノート情報を格納するリスト (音程, 強さ, 絶対時刻, 長さ)
        time = 0  # ノートの絶対時刻
        events = []

        for j in range(len(track)):
            message = track[j]
            # debug(f"i={i} of {len(midi_file.tracks)-1}, j={j} of {len(track)-1}", 1)

            time += message.time
            start = None

            message.time *= mlt

            # on命令
            if message.type == "note_on":
                if start == None:
                    start = time

                notes.append(
                    {
                        "pitch": message.note,
                        "tick": time,
                        "length": None,
                    }
                )

            # off命令
            elif message.type == "note_off":
                # 後ろから探索して音程が同じかつまだ長さが設定されていないものを探す
                for note in notes[::-1]:
                    if note["pitch"] == message.note and note["length"] is None:
                        note["length"] = time - note["tick"]
                        break

            else:
                if message.type == "set_tempo":
                    t["tempo"] = message.tempo
                e = vars(message)
                e["tick"] = time
                e.pop("time")
                events.append(e)

            if start is not None:
                t["start"] = min(t["start"], start)

        t["tracks"].append({"length": time, "notes": notes, "events": events})

    t["length"] = max(track["length"] for track in t["tracks"])
    t["selected_track"] = 0

    print()
    save(t)

    return t


# midiファイルを選択する
def click_fileselect():
    file_path = tkinter.filedialog.askopenfilename(filetypes=[("midi", ".mid")])

    if len(file_path) == 0:
        addlog("MIDIが選択されなかったのだ")
        return None

    if get_file_extension(file_path) != ("mid" or "midi"):
        addlog("MIDIファイルを選択して、なのだ")
        return None

    read_midi_file(file_path)


def draw_all_notes():
    if translated_midi_file is None:
        addlog("MIDIが選択されていないのだ")
        return None

    # キャンバスをクリア
    canvas.delete("all")

    scale = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]

    for y in range(128):
        colour = "#ddddff"
        if scale[(y + 9) % 12] == 0:
            colour = "#ffffff"

        canvas.create_rectangle(
            0, y * 8, translated_midi_file["length"] / 24, (y + 1) * 8, fill=colour
        )
    off_set_x = translated_midi_file["start"]

    for y in range(int(128 / 12)):
        canvas.create_line(
            0,
            (y * 12 + 8) * 8,
            translated_midi_file["length"] / 24,
            (y * 12 + 8) * 8,
            fill="#000000",
            width=2,
        )

    for x in range(int(translated_midi_file["length"] / 1920)):
        canvas.create_line(
            x * 80 + off_set_x / 24,
            0,
            x * 80 + off_set_x / 24,
            canvas["height"] * 3,
            fill="#636363",
        )

    for t in range(len(translated_midi_file["tracks"])):
        draw_notes(t, "#777777")

    draw_notes(translated_midi_file["selected_track"], "#7777ff")


def draw_notes(track_num: int, colour: str):
    if translated_midi_file is None:
        addlog("MIDIが選択されていないのだ")
        return None

    t = translated_midi_file

    # ノートの描画
    for note in t["tracks"][track_num]["notes"]:
        if note["length"] is not None:
            # ノートの長さを計算
            x1 = note["tick"] / 24
            x2 = x1 + note["length"] / 24
            y1 = (127 - note["pitch"]) * 8
            y2 = y1 + 8

            if track_num == 10:
                canvas.create_oval(x1 - 5, y1 - 1, x1 + 5, y2 + 1, fill=colour)
            else:
                canvas.create_rectangle(x1, y1, x2, y2, fill=colour)

    canvas.config(scrollregion=(0, 0, 480 + t["length"] / 24, 640))


def track_select(event):
    if translated_midi_file is not None:
        translated_midi_file["selected_track"] = int(event.widget.get())
        # save(translated_midi_file)

        addlog(event.widget.get() + "番にトラックを変更したのだ")

    draw_all_notes()


def button_play():
    global midi_player

    if midi_player["is_playing"]:
        midi_stop()
        return None

    if midi_file is None:
        addlog("MIDIが選択されていないのだ")
        return None

    addlog("再生を開始するのだ")
    button0["text"] = "□"

    midi_player["is_playing"] = True

    # スレッドの生成とスタート
    thread0 = threading.Thread(target=midi_play, daemon=True)
    thread0.start()


def midi_stop():
    midi_player["is_playing"] = False
    button0["text"] = "▷"


def midi_play():
    duration = 0

    ports = mido.get_output_names()
    with mido.open_output(ports[0]) as outport:
        for msg in midi_file:
            duration += msg.time * 480 * 1000 * 1000 / translated_midi_file["tempo"]
            if midi_player["is_playing"]:
                # 指定位置まで超速再生
                if int(label1["text"]) <= duration:
                    time.sleep(msg.time)
                elif msg.type == "note_on":
                    msg.velocity = 0

                if not msg.is_meta:
                    outport.send(msg)

    midi_stop()
    addlog("再生を終了したのだ")


def key_action(event):
    print(event.keysym)

    if event.keysym in key_listener.keys():
        key_listener[event.keysym]()


def click_close():
    midi_stop()
    for p in processes:
        p.kill()
    root.destroy()


def click_canvas(event):
    label1["text"] = canvas.canvasx(event.x) * 24 + 120

    label1["text"] = int(label1["text"]) - int(label1["text"]) % 120
    pass


def save(t_midi):
    with open(path + "/translated_midi.json", "wt") as f:
        json.dump(t_midi, f)
    addlog("translated_midiを保存したのだ")


# ---------------------------------------------------------------------------


# can_drop_file = {"ex": function}
can_drop_file = {}
can_drop_file["mid"] = read_midi_file

# listeners = {"key": function}
key_listener = {}

key_listener["space"] = button_play

# 作業しているところ
path = os.getcwd()

midi_player = {"is_playing": False}

midi_file = None

translated_midi_file = None

processes = []


# ----------------------------------------------------------

root = tkinterdnd2.Tk()
root.title("AIこんぽ～ざ～")
root.geometry("960x320")

root.bind("<Key>", key_action)

menubar = tkinter.Menu(root)
root.config(menu=menubar)

file = tkinter.Menu(menubar, tearoff=0)
menubar.add_cascade(label="File", menu=file)

exe = tkinter.Menu(menubar, tearoff=0)
menubar.add_cascade(label="exe", menu=exe)

frame0 = tkinter.Frame(root, width=360)
frame0.pack(side="left", anchor="n", fill="y")

log = tkinter.Text(frame0, state="disabled")
log.place(x=0, y=20, width=360, relheight=1)
# Scrollbarを生成してCanvasに配置処理
scroll_log = tkinter.Scrollbar(log, orient=tkinter.VERTICAL)
scroll_log.pack(side=tkinter.RIGHT, fill=tkinter.Y)
scroll_log.config(command=log.yview)
log.config(yscrollcommand=scroll_log.set)

# ---------------------------------------------------------------------------

root.protocol("WM_DELETE_WINDOW", click_close)

file.add_command(label="open_midi...", command=click_fileselect)

# ---------------------------------------------------------------------------

label_track_num = tkinter.Label(frame0, text="Track_Num:")
label_track_num.place(x=0, y=0, width=80, height=20)

combobox0 = tkinter.ttk.Combobox(frame0, values=[0], state="readonly")
combobox0.set(0)
combobox0.bind("<<ComboboxSelected>>", track_select)
combobox0.place(x=80, y=0, width=120, height=20)

button0 = tkinter.Button(frame0, text="▷", command=button_play)
button0.place(x=240, y=0, width=20, height=20)

label1 = tkinter.Label(frame0, text="0")
label1.place(x=260, y=0, width=100, height=20)

frame1 = tkinter.Frame(root)
frame1.pack(side="left", anchor="n", fill="both", expand=True)

canvas = tkinter.Canvas(frame1, bg="#151515")
canvas.pack(side="left", anchor="n", fill="both", expand=True)

# Scrollbarを生成してCanvasに配置処理
bar_y = tkinter.Scrollbar(canvas, orient=tkinter.VERTICAL)
bar_x = tkinter.Scrollbar(canvas, orient=tkinter.HORIZONTAL)
bar_y.pack(side=tkinter.RIGHT, fill=tkinter.Y)
bar_x.pack(side=tkinter.BOTTOM, fill=tkinter.X)
bar_y.config(command=canvas.yview)
bar_x.config(command=canvas.xview)
canvas.config(yscrollcommand=bar_y.set, xscrollcommand=bar_x.set)
# Canvasのスクロール範囲を設定
canvas.config(scrollregion=(0, 0, 480, 640))

canvas.drop_target_register(tkinterdnd2.DND_FILES)
canvas.dnd_bind("<<Drop>>", drop_file)

canvas.bind("<Button-1>", click_canvas)


if os.path.exists(path + "/translated_midi.json"):
    with open(path + "/translated_midi.json", "r") as f:
        translated_midi_file = json.load(f)
        combobox0["values"] = list(range(len(translated_midi_file["tracks"])))
        combobox0.set(translated_midi_file["selected_track"])

        draw_all_notes()
