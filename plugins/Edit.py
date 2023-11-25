import tkinter.simpledialog as simpledialog

from window import edit, load_com, addlog


def load_module():
    def menu_rename_track():
        from window import com_files, com_select

        if len(com_files) == 0:
            return

        new_name = simpledialog.askstring("New Name", "Enter New Name")

        if new_name is None:
            return

        com = com_files[com_select]
        track = com.data["tracks"][com.data["selected_track"]]

        track["track_name"] = new_name

        load_com()

        addlog("track_nameを変更したのだ")

    def menu_rename_cmcm():
        from window import com_files, com_select

        if len(com_files) == 0:
            return

        new_name = simpledialog.askstring("New Name", "Enter New Name")

        if new_name is None:
            return
        com = com_files[com_select]

        com.data["name"] = new_name

        load_com()

        addlog("cmcm_fileの名前を変更したのだ")

    edit.add_command(label="rename_track...", command=menu_rename_track)
    edit.add_command(label="rename_cmcm...", command=menu_rename_cmcm)
