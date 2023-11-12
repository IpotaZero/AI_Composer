import json
import os

import numpy as np

import tkinter
import tkinter.ttk

import mido
from window import *
from mido import Message, MidiFile, MidiTrack, MetaMessage


def Learn():
    def learning(phrase):
        connections = []

        # 生成用データの取得(あれば)
        if os.path.exists(path + "/plugins/AI/Com_trainingdata.json"):
            with open(path + "/plugins/AI/Com_trainingdata.json") as f:
                data = json.load(f)
                connections = data["connections"]

        # 最大の部分配列サイズ
        max_melody_length = 16

        for i in range(len(phrase)):
            # 部分配列サイズの制限
            max_size = min(len(phrase) - i, max_melody_length)

            for j in range(max_size):
                debug(f"i={i} of {len(phrase) - 1}, j={j} of {max_size - 1}")

                # 部分配列を取得
                subphrase = phrase[i : i + j + 1]

                # 既存の部分配列リストで一致するものを探す
                connection = next((c for c in connections if c["a"] == subphrase), None)

                # 部分配列が既に存在する場合
                if connection is not None:
                    # 部分配列の次の要素がフレーズ内に存在するなら
                    if i + j + 1 < len(phrase):
                        entry_index = next(
                            (
                                k
                                for k in range(len(connection["b"]))
                                if connection["b"][k] == phrase[i + j + 1]
                            ),
                            None,
                        )

                        if entry_index is not None:
                            connection["c"][entry_index] += 1

                        else:  # 次の要素が未登録の場合
                            # 次の要素を追加
                            connection["b"].append(phrase[i + j + 1])
                            connection["c"].append(1)

                # 部分配列が存在しない場合
                else:
                    # 新しい部分配列を登録
                    connections.append({"a": subphrase, "b": [], "c": []})
                    # 部分配列の次の要素がフレーズ内に存在するか確認
                    if i + j + 1 < len(phrase):
                        # 次の要素を追加
                        connections[-1]["b"].append(phrase[i + j + 1])
                        connections[-1]["c"].append(1)

        return {"connections": connections}

    # midiファイルを学習用データに変換
    def print_midi(file: mido.MidiFile, track_num: int):
        note_data = []
        current_note = 0

        track = file.tracks[track_num]

        for message in track:
            if message.type == "note_on":
                if message.time > 0:
                    # 休符を表すデータを追加
                    note_data.append([-1, message.time])

                current_note = message.note

            elif message.type == "note_off":
                # ノートとその長さを追加
                note_data.append([current_note, message.time])

        return note_data

    # -----------------------------------------------------------------------

    def on_ask_window_close():
        addlog("学習がキャンセルされたのだ")
        ask_window.destroy()

    def run(track_num: int):
        ask_window.destroy()

        addlog("こんちゃん1号学習開始...")

        from window import midi_file

        if midi_file is None:
            addlog("MIDIないのだ！")
            return None

        # 学習用データの用意
        note_data = print_midi(midi_file, track_num)

        # 学習(生成用データの作成)
        data = learning(note_data)

        # 生成用データを保存
        with open(path + "/plugins/AI/Com_trainingdata.json", "wt") as f:
            json.dump(data, f)

        print("\n")

        addlog("学習が完了したのだ")

    ask_window = tkinter.Toplevel(root)
    ask_window.title("学習するトラックを選択するのだ")
    ask_window.geometry("400x100")
    ask_window.protocol("WM_DELETE_WINDOW", on_ask_window_close)

    combobox_track_num = tkinter.ttk.Combobox(
        ask_window, values=list(range(16)), state="readonly"
    )
    combobox_track_num.set(0)
    combobox_track_num.pack()

    button_run = tkinter.Button(
        ask_window, text="Run", command=lambda: run(int(combobox_track_num.get()))
    )
    button_run.pack()


def Generate() -> mido.MidiFile:
    def generate_melody(key_note):
        # 生成用データの取得
        with open(path + "/plugins/AI/Com_trainingdata.json") as f:
            data = json.load(f)

        connections = data["connections"]

        note_count = 0
        mutation_count = 0

        if not next((c for c in connections if c["a"] == [key_note]), None):
            addlog("key_noteを見直せください")
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

        addlog("melody: " + str(melody))

        mutation_rate = mutation_count / note_count if note_count > 0 else 0
        addlog("変異率: " + str(mutation_rate))

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
        addlog("生成がキャンセルされたのだ")
        ask_window.destroy()

    def run(key_note: int, bpm: int):
        ask_window.destroy()

        # 生成用データありますか
        if not os.path.exists(path + "/plugins/AI/Com_trainingdata.json"):
            addlog("生成用データが存在しないのだ")
            return None

        # 保存先を確認
        save_path = tkinter.filedialog.asksaveasfilename(filetypes=[("midi", ".mid")])
        if len(save_path) == 0:
            addlog("生成がキャンセルされたのだ")
            return None

        addlog("生成開始...")

        # メロディ配列を生成
        melody = generate_melody([key_note, 480])

        # 配列をmidiに変換
        make_midi_file(melody, bpm).save(save_path)

        print("\n")

        addlog("生成が完了したのだ")
        read_midi_file(save_path)

    def click_button():
        key_note = int(combobox_key_note.get())
        bpm = int(combobox_bpm.get())

        run(key_note, bpm)

    ask_window = tkinter.Toplevel(root)
    ask_window.title("主音を選択するのだ(C4=60)")
    ask_window.geometry("400x100")
    ask_window.protocol("WM_DELETE_WINDOW", on_ask_window_close)

    combobox_key_note = tkinter.ttk.Combobox(
        ask_window, values=list(range(128)), state="readonly"
    )
    combobox_key_note.set(72)
    combobox_key_note.pack()

    combobox_bpm = tkinter.ttk.Combobox(
        ask_window, values=list(range(300)), state="readonly"
    )
    combobox_bpm.set(120)
    combobox_bpm.pack()

    button_run = tkinter.Button(ask_window, text="Run", command=click_button)
    button_run.pack()


def Introduce():
    ask_window = tkinter.Toplevel(root)
    ask_window.title("AI紹介")
    ask_window.geometry("400x100")

    text = tkinter.Text(ask_window)
    text.pack(anchor="nw", fill="both", expand=True)

    text.insert(tkinter.END, "名前:こんちゃん1号\n")
    text.insert(tkinter.END, "最初に作成された作曲AI、マルコフ連鎖を利用している\n")
    text.insert(tkinter.END, "一本線のメロディしか学習できないのが難点\n")
    text.insert(tkinter.END, "midiを読み込んだ後Learnを押しトラックを選択\n")
    text["state"] = "disabled"
