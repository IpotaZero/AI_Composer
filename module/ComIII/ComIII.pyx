# distutils: language=c++
# distutils: extra_compile_args = ["-O3"]
# cython: language_level=3, boundscheck=False, wraparound=True
# cython: cdivision=True

import json
import math
import os
import time
import tkinter
import tkinter.filedialog
import tkinter.ttk
import numpy as np
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

from window import *

cdef learning(phrases):
    connections = []

    # 生成用データの取得(あれば)
    if os.path.exists(path + "/plugins/AI/Com3_trainingdata.json"):
        with open(path + "/plugins/AI/Com3_trainingdata.json") as f:
            data = json.load(f)
            connections = data["connections"]

    # 最大の部分配列サイズ
    max_melody_length = 16

    debug(reset=True)

    for h in range(len(phrases)):
        phrase = phrases[h]

        for i in range(len(phrase)):
            debug(f"h={h} of {len(phrases)-1}, i={i} of {len(phrase) - 1}",1)

            # 部分配列サイズの制限
            max_size = min(len(phrase) - i, max_melody_length)

            for j in range(max_size):
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
cdef print_midi(translated_midi):
    track_num = translated_midi["selected_track"]

    # 長さの最小単位
    resolution = 1

    notes = translated_midi["tracks"][track_num]["notes"]

    phrases = []

    interval = 1920 * 4

    # 長さの単位の変換とか
    for n in notes:
        t = int(n["tick"] / interval)
        while len(phrases) <= t:
            phrases.append([])
        phrases[t].append(
            [
                n["pitch"],
                int(n["tick"] % interval / resolution),
                math.ceil(min(n["length"], 1920) / resolution),
            ]
        )

    # 重なりの排除
    neo_phrases = []

    for phrase in phrases:
        if len(phrase) > 0:
            neo_phrase = []

            # 調を推測する
            pitch_list = [0] * 12
            for note in phrase:
                pitch_list[note[0] % 12] = 1

            maj = [1, 0, 1, 0.1, 1, 0.8, 0, 0.9, 0.1, 1, 0, 0.8]

            devation = []
            for i in range(12):
                key = maj[-i:] + maj[:-i]
                S = sum((key[j] - pitch_list[j]) ** 2 for j in range(12))
                devation.append(S)

            key = devation.index(min(devation))

            # print("key:", key, ", melody:", phrase)
            # print(devation)

            current_note = phrase[0]
            neo_phrase.append(current_note)

            for i in range(1, len(phrase)):
                note = phrase[i]

                # 位置が完全に一致
                if current_note[1] == note[1]:
                    neo_phrase.pop()
                    current_note = max(current_note, note)

                # 重なっている
                elif current_note[1] < note[1] < current_note[1] + current_note[2]:
                    neo_phrase[-1][2] = note[1] - current_note[1]
                    current_note = note

                else:
                    current_note = note

                neo_phrase.append(current_note)

            neo_phrases.append(
                [
                    [neo_phrase[i][0] - key, neo_phrase[i][1], neo_phrase[i][2]]
                    for i in range(len(neo_phrase))
                ]
            )

    # 休符を使って絶対位置を消去
    neo_phrases2 = []

    for neo_phrase in neo_phrases:
        neo_phrase2 = []
        current_time = 0
        for note in neo_phrase:
            if current_time < note[1]:
                neo_phrase2.append([-1, note[1] - current_time])
                current_time = note[1]

            neo_phrase2.append([note[0], note[2]])
            current_time += note[2]

        neo_phrases2.append(neo_phrase2)

    return neo_phrases2


cpdef Learn():
    addlog("こんちゃん3号学習開始...")

    # midi
    if not os.path.exists(path + "/translated_midi.json"):
        print("There is no translated_midi")

    else:
        start = time.time()

        translated_midi = None

        with open(path + "/translated_midi.json") as f:
            translated_midi = json.load(f)

        # 学習用データの用意
        note_data = print_midi(translated_midi)

        # print(note_data)

        # 学習(生成用データの作成)
        data = learning(note_data)

        # 生成用データを保存
        with open(path + "/plugins/AI/Com3_trainingdata.json", "wt") as f:
            json.dump(data, f)

        print("\n")

        print(time.time() - start)

        addlog("学習が完了したのだ")

#----------------------------------------------------------------------------------------------------

cdef generate_melody(key_note):
    # 生成用データの取得
    with open(path + "/plugins/AI/Com3_trainingdata.json") as f:
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
def make_midi_file(melody, bpm):
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

cpdef Generate():
    # 生成用データありますか
    if not os.path.exists(path + "/plugins/AI/Com3_trainingdata.json"):
        addlog("生成用データが存在しないのだ")
        return None

    # 保存先を確認
    save_path = tkinter.filedialog.asksaveasfilename(filetypes=[("midi", ".mid")])
    if len(save_path) == 0:
        addlog("生成がキャンセルされたのだ")
        return None

    addlog("生成開始...")

    # メロディ配列を生成
    melody = generate_melody([72, 480])

    # 配列をmidiに変換
    make_midi_file(melody, 168).save(save_path)

    print("\n")

    addlog("生成が完了したのだ")
    read_midi_file(save_path)

cpdef Introduce():
    ask_window = tkinter.Toplevel(root)
    ask_window.title("AI紹介")
    ask_window.geometry("400x100")

    text = tkinter.Text(ask_window)
    text.pack(anchor="nw", fill="both", expand=True)

    text.insert(tkinter.END, "名前:こんちゃん3号\n")
    text.insert(tkinter.END, "第3の作曲AI、マルコフ連鎖を利用している\n")
    text.insert(tkinter.END, "メロディを解析することによって学習量を増やすことが狙い\n仕組みとしてはこんちゃん1号と近い\n")
    text.insert(tkinter.END, "translated_midiさえあればmidiを読み込んでいなくても学習可能\n")
    text.insert(tkinter.END, "解析の性質上key=Cに固定される\n")
    text.insert(tkinter.END, "めんどかったのでbpm=168で固定\n")
    text["state"] = "disabled"
