import tkinter.simpledialog as simpledialog
import tkinter as tk
import mido
import json

from window import edit, load_com, addlog, log_notes, log_events, root


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

        com.com_changed = True

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

        com.com_changed = True

        addlog("cmcmの名前を変更したのだ")

    def menu_add_message():
        from window import com_files, com_select, midi_player

        if len(com_files) == 0:
            return

        new_message_type = simpledialog.askstring("Type of New Message", "Enter Type")

        com = com_files[com_select]
        t = com.data["selected_track"]

        try:
            m = mido.Message.from_dict({"type": new_message_type}).dict()
        except:
            m = mido.MetaMessage.from_dict({"type": new_message_type}).dict()

        m["tick"] = midi_player.current_time
        print(m)
        com.data["tracks"][t]["events"].append(m)

        com.com_changed = True

        load_com()

    def on_select_message(event):
        def on_click_ok():
            for naiyou in naiyous:
                if naiyou == "type":
                    continue
                g = t[naiyou]["entry"].get()
                if str.isnumeric(g):
                    g = int(g)
                    if naiyou == "pitch" and g > 127:
                        continue

                    default_value[naiyou] = g

            from window import com_files, com_select

            if len(com_files) == 0:
                return
            com = com_files[com_select]

            if event.widget == log_notes:
                key = "notes"
            else:
                key = "events"

            messages = com.data["tracks"][com.data["selected_track"]][key]
            messages.pop(index)
            messages.append(default_value)

            com.data["tracks"][com.data["selected_track"]][key] = sorted(
                messages, key=lambda x: x["tick"]
            )

            com.com_changed = True

            load_com()

            window_ask.destroy()

        index = event.widget.curselection()[0]
        default_value = json.loads(event.widget.get(index).replace("'", '"'))

        naiyous = default_value.keys()

        window_ask = tk.Toplevel(root)
        window_ask.geometry("240x240")
        window_ask.title("Remodel Message")
        t = {}
        for i, naiyou in enumerate(naiyous, 1):
            if naiyou == "type":
                continue
            t[naiyou] = {}
            t[naiyou]["label"] = tk.Label(window_ask, text=naiyou)
            t[naiyou]["entry"] = tk.Entry(window_ask)
            t[naiyou]["entry"].insert(0, default_value[naiyou])

            t[naiyou]["label"].place(x=20, y=20 * i)
            t[naiyou]["entry"].place(x=100, y=20 * i)

        button_ok = tk.Button(window_ask, width=12, text="OK", command=on_click_ok)
        button_ok.place(x=70, y=20 * (i + 2))
        window_ask.bind("<Key-Return>", lambda event: on_click_ok())

    edit.add_command(label="rename_track...", command=menu_rename_track)
    edit.add_command(label="rename_cmcm...", command=menu_rename_cmcm)
    edit.add_command(label="add_message...", command=menu_add_message)

    log_notes.bind("<Double-Button-1>", on_select_message)
    log_events.bind("<Double-Button-1>", on_select_message)
