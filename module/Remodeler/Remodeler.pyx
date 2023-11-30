import tkinter.simpledialog as simpledialog
import tkinter as tk
import mido
import json

from window import (
    menu_edit,
    load_com,
    addlog,
    log_notes,
    log_events,
    root,
    resolve_overlapping,
    Com_file,
)


def load_module():
    def on_menu_rename_track():
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

    def on_menu_rename_cmcm():
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

    def on_menu_add_message():
        from window import com_files, com_select, midi_player

        if len(com_files) == 0:
            return

        new_message_type = simpledialog.askstring("Type of New Message", "Enter Type")

        com = com_files[com_select]
        t = com.data["selected_track"]

        if new_message_type == ("note_on" or "note_off"):
            return

        try:
            m = mido.Message.from_dict({"type": new_message_type}).dict()
        except:
            m = mido.MetaMessage.from_dict({"type": new_message_type}).dict()

        m["tick"] = midi_player.current_tick
        print(m)
        com.data["tracks"][t]["messages"].append(m)

        com.com_changed = True

        load_com()

    def on_select_message(event):
        def on_click_delete():
            if key == "events":
                messages = com.get_events(com.data["selected_track"])
                other = com.get_notes(com.data["selected_track"])
            else:
                messages = com.get_notes(com.data["selected_track"])
                other = com.get_events(com.data["selected_track"])

            print(com.get_events(com.data["selected_track"]))

            messages.pop(index)

            com.data["tracks"][com.data["selected_track"]]["messages"] = sorted(
                other + messages, key=lambda x: x["tick"]
            )
            com.com_changed = True
            load_com()
            window_ask.destroy()

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

            if key == "events":
                messages = com.get_events(com.data["selected_track"])
                other = messages = com.get_notes(com.data["selected_track"])
            else:
                messages = com.get_notes(com.data["selected_track"])
                other = com.get_events(com.data["selected_track"])

            messages.pop(index)
            messages.append(default_value)

            com.data["tracks"][com.data["selected_track"]]["messages"] = sorted(
                other + messages, key=lambda x: x["tick"]
            )

            com.com_changed = True

            load_com()

            window_ask.destroy()

        from window import com_files, com_select

        if len(com_files) == 0:
            return
        com: Com_file = com_files[com_select]

        index = event.widget.curselection()[0]
        default_value = json.loads(event.widget.get(index).replace("'", '"'))
        naiyous = default_value.keys()

        if event.widget == log_notes:
            key = "notes"
        else:
            key = "events"

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

        button_ok = tk.Button(window_ask, width=6, text="OK", command=on_click_ok)
        button_ok.place(x=55, y=20 * (i + 2))

        button_delete = tk.Button(
            window_ask, width=6, text="Delete", command=on_click_delete
        )
        button_delete.place(x=130, y=20 * (i + 2))

        window_ask.bind("<Key-Return>", lambda event: on_click_ok())

    def menu_resolve_overlapping():
        from window import com_files, com_select

        if len(com_files) == 0:
            return

        com = com_files[com_select]

        track_num = com.data["selected_track"]

        com = com_files[com_select]

        notes = com.get_notes(track_num)
        events = com.get_events(track_num)

        neo_notes = resolve_overlapping(notes)

        com.data["tracks"][com.data["selected_track"]]["messages"] = sorted(
            events + neo_notes, key=lambda m: m["tick"]
        )

        com.com_changed = True
        addlog("重複を解消したのだ")
        load_com()

    menu_edit.add_command(label="rename_track...", command=on_menu_rename_track)
    menu_edit.add_command(label="rename_cmcm...", command=on_menu_rename_cmcm)
    menu_edit.add_command(label="add_message...", command=on_menu_add_message)
    menu_edit.add_command(label="resolve overlapping", command=menu_resolve_overlapping)

    log_notes.bind("<Double-Button-1>", on_select_message)
    log_events.bind("<Double-Button-1>", on_select_message)
