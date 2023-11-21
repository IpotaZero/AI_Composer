import glob
import sys
from window import *

import tkinter as tk
import tkinter.filedialog
import os


def load_module():
    # 学習
    def click_learn(fn):
        from window import translated_midi_file

        save(translated_midi_file)

        # スレッドの生成とスタート
        thread_learn = threading.Thread(target=fn, daemon=True)
        thread_learn.start()

    # 生成
    def click_generate(fn):
        # スレッドの生成とスタート
        thread_generate = threading.Thread(target=fn, daemon=True)
        thread_generate.start()

    # print(path)

    ai_path = path + "/plugins/AI"
    sys.path.append(ai_path)

    ais = {}

    for ppath in glob.glob(ai_path + "/*"):
        if get_file_extension(ppath) == "pyd" or os.path.basename(ppath) == "ComIV.py":
            name = os.path.basename(ppath).split(".")[0]
            ais[name] = {}
            ais[name]["module"] = importlib.import_module(name)
            ais[name]["learn"] = getattr(
                ais[name]["module"], "Learn", None
            )  # Get the "learn" function
            ais[name]["generate"] = getattr(
                ais[name]["module"], "Generate", None
            )  # Get the "generate" function

    # print(ai_module)

    ai = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="AI", menu=ai)

    for ai_name in ais.keys():
        ais[ai_name]["menu"] = tk.Menu(ai, tearoff=0)

        ai.add_cascade(label=ai_name, menu=ais[ai_name]["menu"])

        if ais[ai_name]["learn"]:
            ais[ai_name]["menu"].add_command(
                label="learn...",
                command=lambda ai_name=ai_name: click_learn(ais[ai_name]["learn"]),
            )
        if ais[ai_name]["generate"]:
            ais[ai_name]["menu"].add_command(
                label="generate...",
                command=lambda ai_name=ai_name: click_generate(
                    ais[ai_name]["generate"]
                ),
            )
        if hasattr(ais[ai_name]["module"], "Introduce"):
            ais[ai_name]["menu"].add_command(
                label="introduction...",
                command=ais[ai_name]["module"].Introduce,
            )

        addlog(ai_name + "をロードしたのだ")
