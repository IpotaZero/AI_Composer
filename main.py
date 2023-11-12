import glob
import importlib
import os
import subprocess
import sys

from window import root, get_file_extension, addlog, path, exe

# ----------------------------------------------------------------------------------------


# プラグインの読み込み
plugins_path = path + "/plugins"

sys.path.append(plugins_path)

plugins = {}

exes = {}

for ppath in glob.glob(plugins_path + "/*"):
    ex = get_file_extension(ppath)
    name = os.path.split(ppath)[1].split(".")[0]

    if ex == "py":
        plugins[name] = importlib.import_module(name)
    elif ex == "exe":
        exes[name]["path"] = ppath
        exes[name]["function"] = lambda: subprocess.Popen(ppath)
        exe.add_command(label=name, command=exes[name]["function"])

addlog("プラグインのロード開始...")
addlog(str(plugins.keys()))
for name in plugins.keys():
    plugins[name].load_module()

addlog("プラグインをロードしたのだ")

# import関係
# window -> plugin -> main
# window -> main

# 実行
root.mainloop()
