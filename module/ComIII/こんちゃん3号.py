import json
import os

import numpy as np

import tk
import tk.filedialog
import tk.ttk

import mido
from window import *
from mido import Message, MidiFile, MidiTrack, MetaMessage

import threading
from ComIII_learning import run


def Learn():
    from window import com_files[com_select].data

    save(com_files[com_select].data)

    thread_lerning = threading.Thread(target=run, daemon=True)
    thread_lerning.start()


def Generate() -> mido.MidiFile:
    def generate_melody(key_note):
        # 生成用データの取得
        with open(path + "/plugins/AI/Com3_trainingdata.json") as f:
            data = json.load(f)

        connections = data["connections"]

        note_count = 0
        mutation_count = 0

        if not next((c for c in connections if c["a"] == [key_note]), None):
            # addlog("key_noteを見直せください")
            return []

        premelody = [key_note]
        melody = [key_note]

        max_length = 480 * 4 * 16

        length = 0
        while length < max_length:
            if np.random.random() < 0.1:
                premelody = [key_note]
                mutation_count += 1

            # power内を探索
            connection = next((c for c in connections if c["a"] == premelody), None)

            # 登録されていて、かつ次の音が存在する場合
            if connection is not None and len(connection["b"]) > 0:
                # 次の音が存在するなら
                selected_index = np.random.choice(
                    len(connection["b"]),
                    p=np.array(connection["c"]) / sum(connection["c"]),
                )

                # 音をランダムに選択
                selected_note = connection["b"][selected_index]

                note_count += 1
                premelody.append(selected_note)
                melody.append(selected_note)

                # 長さを加算
                length += selected_note[1]

                debug(f"selected_note: {selected_note}, length: {length}")

            # 登録されていない、または次の音がない場合
            else:
                # 先頭の音を削除して再探索
                premelody.pop(0)

                # 完全に存在しない場合
                if len(premelody) == 0:
                    # 主音に戻る
                    premelody = [key_note]

        # addlog("melody: " + str(melody))

        mutation_rate = mutation_count / note_count if note_count > 0 else 0
        # addlog("変異率: " + str(mutation_rate))

        return melody

    # 配列からmidiファイルを生成
    def make_midi_file(melody, bpm) -> mido.MidiFile:
        # midiファイルを作る
        mid = MidiFile()
        # トラックを作る
        track = MidiTrack()
        # トラックをmidiファイルに入れる
        mid.tracks.append(track)
        # BPM
        track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))

        def append_note(note, length, time):
            track.append(Message("note_on", velocity=127, note=note, time=time))
            track.append(Message("note_off", note=note, time=length))

        duration = 0

        for note in melody:
            if note[0] == -1:
                # 休符
                duration += note[1]
            else:
                # 音符
                append_note(note[0], note[1], duration)
                duration = 0

        return mid

    # ------------------------------------------------------------------------------------------

    def on_ask_window_close():
        # addlog("生成がキャンセルされたのだ")
        ask_window.destroy()

    def run(key_note: int, bpm: int):
        ask_window.destroy()

        # 生成用データありますか
        if not os.path.exists(path + "/plugins/AI/Com_trainingdata.json"):
            # addlog("生成用データが存在しないのだ")
            return None

        # 保存先を確認
        save_path = tk.filedialog.asksaveasfilename(filetypes=[("midi", ".mid")])
        if len(save_path) == 0:
            # addlog("生成がキャンセルされたのだ")
            return None

        # addlog("生成開始...")

        # メロディ配列を生成
        melody = generate_melody([key_note, 480])

        # 配列をmidiに変換
        make_midi_file(melody, bpm).save(save_path)

        print("\n")

        # addlog("生成が完了したのだ")
        read_midi_file(save_path)

    def click_button():
        key_note = int(combobox_key_note.get())
        bpm = int(combobox_bpm.get())

        run(key_note, bpm)

    ask_window = tk.Toplevel(root)
    ask_window.title("主音を選択するのだ(C4=60)")
    ask_window.geometry("400x100")
    ask_window.protocol("WM_DELETE_WINDOW", on_ask_window_close)

    combobox_key_note = tk.ttk.Combobox(
        ask_window, values=list(range(128)), state="readonly"
    )
    combobox_key_note.set(72)
    combobox_key_note.pack()

    combobox_bpm = tk.ttk.Combobox(
        ask_window, values=list(range(300)), state="readonly"
    )
    combobox_bpm.set(120)
    combobox_bpm.pack()

    button_run = tk.Button(ask_window, text="Run", command=click_button)
    button_run.pack()


def Introduce():
    ask_window = tk.Toplevel(root)
    ask_window.title("AI紹介")
    ask_window.geometry("400x100")

    text = tk.Text(ask_window)
    text.pack(anchor="nw", fill="both", expand=True)

    text.insert(tk.END, "名前:こんちゃん3号\n")
    text.insert(tk.END, "第3の作曲AI、マルコフ連鎖を利用している\n")
    text.insert(tk.END, "メロディを解析することによって学習量を増やすことが狙い\n仕組みとしてはこんちゃん1号と近い\n")
    text["state"] = "disabled"
