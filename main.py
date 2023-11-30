import glob
import importlib
import os
import subprocess
import sys

from window import root, get_file_extension, addlog, menu_exe, processes


# ----------------------------------------------------------------------------------------
def add_process(path):
    processes.append(subprocess.Popen(path))

    # print(processes)


def main():
    # プラグインの読み込み
    plugins_path = "./plugins"

    sys.path.append(plugins_path)

    plugins = {}

    exes = {}

    for ppath in glob.glob(plugins_path + "/*"):
        ex = get_file_extension(ppath)
        name = os.path.split(ppath)[1].split(".")[0]

        if ex == "pyd" or ex == "py":
            plugins[name] = importlib.import_module(name)
        elif ex == "exe":
            exes[name] = {}
            exes[name]["path"] = ppath
            exes[name]["function"] = lambda: add_process(ppath)
            menu_exe.add_command(label=name, command=exes[name]["function"])

    addlog("start_loading_plugins")
    addlog(str(plugins.keys()))
    for name in plugins.keys():
        plugins[name].load_module()

    addlog("plugins_are_loaded")

    # import関係
    # window -> plugin -> main
    # window -> main

    # 実行
    root.mainloop()


if __name__ == "__main__":
    main()
