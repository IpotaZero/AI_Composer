import glob
import sys
from window import menubar, get_file_extension, addlog
import threading

import importlib

import tkinter as tk
import os


def load_module():
    def run(a, b):
        fn = ais[a]["function"][b]
        # スレッドの生成とスタート
        thread_learn = threading.Thread(target=fn, daemon=True)
        thread_learn.start()

    ai_path = "./plugins/AI"
    sys.path.append(ai_path)

    ais = {}

    for ppath in glob.glob(ai_path + "/*"):
        ex = get_file_extension(ppath)
        if ex == "pyd" or ex == "py":
            name = os.path.basename(ppath).split(".")[0]
            ais[name] = {}
            ais[name]["module"] = importlib.import_module(name)

            ais[name]["function"] = {}

            for f in ais[name]["module"].load_module():
                print(f.__name__)
                ais[name]["function"][f.__name__] = f

    # print(ai_module)

    menu_ai = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="AI", menu=menu_ai)

    for ai_name in ais:
        ais[ai_name]["menu"] = tk.Menu(menu_ai, tearoff=0)

        menu_ai.add_cascade(label=ai_name, menu=ais[ai_name]["menu"])

        for f_name in ais[ai_name]["function"]:
            ais[ai_name]["menu"].add_command(
                label=f_name,
                command=lambda ai_name=ai_name, f_name=f_name: run(ai_name, f_name),
            )

        addlog(ai_name + "をロードしたのだ")
