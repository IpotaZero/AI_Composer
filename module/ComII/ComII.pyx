import json
import math
import os
import numpy as np
import copy

import tk
import tk.ttk
import tk.filedialog

import mido
from window import *
from mido import Message, MidiFile, MidiTrack, MetaMessage


def Learn():
    # midiファイルを読み込み、学習用の形式に変換する
    def read_midi_file(track_num: int):
        # 長さの最小単位
        resolution = 1

        notes = translated_midi_file["tracks"][track_num]["notes"]

        phrases = []

        interval = 1920 * 4

        # 長さの単位の変換とか
        for n in notes:
            t = int(n["tick"] / interval)
            while len(phrases) <= t:
                phrases.append([])
            n["tick"] = int(n["tick"] % interval / resolution)
            n["tick"] = math.ceil(min(n["length"], 1920) / resolution)
            phrases[t].append([n["pitch"], n["tick"], n["length"]])

        return phrases

    # 音符同士の関係をカウントする
    def count_note(phrases, weight):
        data = {"connections": []}
        connections = []

        # 今までの学習を引用する(あれば)
        if os.path.exists(path + "/plugins/AI/Com2_trainingdata.json"):
            with open(path + "/plugins/AI/Com2_trainingdata.json") as f:
                data = json.load(f)
                connections = data["connections"]
                addlog("学習データを読み込んだのだ")

        for h in range(len(phrases)):
            phrase = phrases[h]
            for i in range(len(phrase)):
                # phrase[i]の関係を探す
                connection = next(
                    (entry for entry in connections if entry["a"] == phrase[i]),
                    None,
                )

                # 存在しないなら追加する
                if connection is None:
                    connection = {"a": phrase[i], "b": [], "c": []}
                    connections.append(connection)

                for j in range(len(phrase)):
                    if i != j:
                        debug(
                            f"h={h} in {len(phrases)-1}, i={i} in {len(phrase)-1}, j={j} in {len(phrase)-1}"
                        )

                        # 相対的な位置を見る
                        note = [
                            phrase[j][0],
                            phrase[j][1] - connection["a"][1],
                            phrase[j][2],
                        ]

                        # 周りの音(phrase[j])を見て、それがphrase[i]とすでに関係づけられているか確認する
                        index = next(
                            (
                                k
                                for k in range(len(connection["b"]))
                                if note == connection["b"][k]
                            ),
                            None,
                        )
                        # すでに関係づけられているなら
                        if index is not None:
                            # 重要度を加える
                            connection["c"][index] += weight
                        else:
                            # いないなら追加する
                            connection["b"].append(note)
                            connection["c"].append(weight)

        data["connections"] = connections

        return data

    # -----------------------------------------------------------------------

    def on_ask_window_close():
        addlog("学習がキャンセルされたのだ")
        ask_window.destroy()

    def make_thread(track_num, weight):
        ask_window.destroy()

        run(track_num, weight)

    def run(track_num, weight):
        addlog("こんちゃん2号学習開始...")

        # 音符に変換
        # addlog("MIDIを音符に変換...")
        phrases = read_midi_file(track_num)

        # 音符の関係をカウント
        addlog("音符の関係をカウント...")
        data = count_note(phrases, weight)

        # 学習用データを保存
        with open(path + "/plugins/AI/Com2_trainingdata.json", "wt") as f:
            json.dump(data, f)

        print("\n")

        addlog("学習が終了したのだ")

    ask_window = tk.Toplevel(root)
    ask_window.title("学習するトラックを選択するのだ")
    ask_window.geometry("400x100")
    ask_window.protocol("WM_DELETE_WINDOW", on_ask_window_close)

    combobox_track_num = tk.ttk.Combobox(ask_window, values=[0], state="readonly")
    combobox_track_num.set(0)
    combobox_track_num.pack()

    combobox_weight = tk.ttk.Combobox(
        ask_window, values=list(range(1, 10)), state="readonly"
    )
    combobox_weight.set(1)
    combobox_weight.pack()

    button_run = tk.Button(
        ask_window,
        text="Run",
        command=lambda: make_thread(
            int(combobox_track_num.get()), int(combobox_weight.get())
        ),
    )
    button_run.pack()

    if os.path.exists(path + "/translated_midi.json"):
        with open(path + "/translated_midi.json", "r") as f:
            translated_midi_file = json.load(f)
            combobox_track_num["values"] = list(
                range(len(translated_midi_file["tracks"]))
            )
            combobox_track_num.set(translated_midi_file["selected_track"])
    else:
        addlog("translated_midiが存在しないのだ")
        return None


def Generate() -> mido.MidiFile:
    def generate_melody(key_note):
        # 生成用データの取得
        with open(path + "/plugins/AI/Com2_trainingdata.json") as f:
            data = json.load(f)
            connections = data["connections"]

        # 探す
        index_first = next(
            (i for i in range(len(connections)) if key_note == connections[i]["a"][0]),
            None,
        )

        if index_first is None or len(connections[index_first]["b"]) == 0:
            addlog("key_noteを見直せ、のだ")
            return None

        length = 4

        notes = []

        note_num = 24

        interval = 1920 * 4

        for measure in range(length):
            # このメロディのコネクション
            c = {"b": [], "c": []}

            bs = connections[index_first]["b"]
            cs = connections[index_first]["c"]

            # 絶対位置に変換
            for i in range(len(connections[index_first]["b"])):
                c["b"].append(
                    [bs[i][0], bs[i][1] + connections[index_first]["a"][1], bs[i][2]]
                )
                c["c"].append(cs[i])

            debug("length: " + str(len(c["b"])) + str(len(c["c"])))

            if len(c["b"]) != len(c["c"]):
                debug("bとcの長さが違うのはバグです")
                debug(str(c))
                return None

            while len(notes) < note_num * (measure + 1):
                if len(c["b"]) == 0:
                    debug("利用可能な音がなくなったのだ")
                    break

                # 値に比例して選ばれる確率が上がる
                selected_index = np.random.choice(
                    len(c["c"]), p=np.array(c["c"]) / sum(c["c"])
                )

                debug(
                    "selected_index: "
                    + str(selected_index)
                    + "/"
                    + str(len(c["c"]) - 1)
                )

                selected_note = copy.deepcopy(c["b"][selected_index])

                selected_note[1] += interval * measure

                # debug("selected_note: " + str(selected_note))

                # selected_noteと同じpitchのnoteを探す
                same_pitch_notes = [
                    note for note in notes if note[0] == selected_note[0]
                ]

                # 競合の可能性がない場合
                if len(same_pitch_notes) > 0:
                    # 競合の可能性があるなら

                    for same_pitch_note in same_pitch_notes:
                        # 重なっているかの判断
                        a1 = same_pitch_note[1]
                        b1 = same_pitch_note[1] + same_pitch_note[2]

                        a2 = selected_note[1]
                        b2 = selected_note[1] + selected_note[2]

                        # 重なっているなら
                        if (a2 <= b1) and (a1 <= b2):
                            selected_note = None
                            break

                # 選択肢を削除
                c["b"].pop(selected_index)
                c["c"].pop(selected_index)

                if selected_note is None:
                    debug("pitch, tick競合により追加を拒否")
                    continue

                notes.append(selected_note)

                selected_copy = copy.deepcopy(selected_note)

                selected_copy[1] -= measure * interval

                # selected_noteのconnectionを探す
                index = next(
                    (
                        k
                        for k in range(len(connections))
                        if selected_copy == connections[k]["a"]
                    ),
                    None,
                )

                if index is None:
                    debug("selected_noteのconnectionは見つかりませんでした")

                if index is not None:
                    connection = connections[index]

                    # connection["b"]とc["b"]をマージ
                    for k in range(len(connection["b"])):
                        # 絶対位置に変換
                        b_k = [
                            connection["b"][k][0],
                            connection["b"][k][1] + selected_note[1],
                            connection["b"][k][2],
                        ]

                        # b_k==c["b"][l]となるlを探す
                        index_b = next(
                            (l for l in range(len(c["b"])) if c["b"][l] == b_k),
                            None,
                        )

                        if index_b is not None:
                            c_copy = copy.deepcopy(c)
                            c_copy["c"][index_b] += connection["c"][k]
                            c = c_copy
                        else:
                            c["b"].append(b_k)
                            c["c"].append(connection["c"][k])

            addlog(str(measure) + "_end")

        return notes

    def make_midi_file(notes):
        # midiファイルを作る
        mid = MidiFile()
        # トラックを作る
        track = MidiTrack()
        # トラックをmidiファイルに入れる
        mid.tracks.append(track)
        # BPM
        track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(192)))

        messages = []
        for note in notes:
            messages += [
                {
                    "type": "on",
                    "pitch": note[0],
                    "tick": note[1],
                },
                {
                    "type": "off",
                    "pitch": note[0],
                    "tick": (note[1] + note[2]),
                },
            ]

        sorted_messages = sorted(messages, key=lambda x: x["tick"])

        # print(sorted_messages)

        time_count = 0
        for message in sorted_messages:
            if message["type"] == "on":
                track.append(
                    Message(
                        "note_on",
                        velocity=127,
                        note=message["pitch"],
                        time=message["tick"] - time_count,
                    )
                )
            else:
                track.append(
                    Message(
                        "note_off",
                        note=message["pitch"],
                        time=message["tick"] - time_count,
                    )
                )

            time_count = message["tick"]

        return mid

    # ------------------------------------------------------------------------------------------

    def on_ask_window_close():
        addlog("生成がキャンセルされたのだ")
        ask_window.destroy()

    def run(key_note: int, bpm: int):
        ask_window.destroy()

        # 生成用データありますか
        if not os.path.exists(path + "/plugins/AI/Com2_trainingdata.json"):
            addlog("生成用データが存在しないのだ")
            return None

        # 保存先を確認
        save_path = "C:/Ipota/programs/ongaku/child/a.mid"

        save_path = tk.filedialog.asksaveasfilename(filetypes=[("midi", ".mid")])
        if len(save_path) == 0:
            addlog("生成がキャンセルされたのだ")
            return None

        addlog("生成開始...")

        notes = generate_melody(key_note)

        if notes is None:
            addlog("生成に失敗したのだ")
            return None

        print("\n")

        addlog("Melody: " + str(sorted(notes, key=lambda x: x[1])))

        make_midi_file(notes).save(save_path)

        addlog("生成が完了したのだ")
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

    text.insert(tk.END, "名前:こんちゃん2号\n")
    text.insert(tk.END, "次に作成された作曲AI\n")
    text["state"] = "disabled"
