import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading

ser = None
running = False
tire_boxes = {}

# =========================
# PARSE TPMS
# =========================
def parse_tire_data(data):

    if len(data) < 10:
        return None, "Waiting..."

    if data[0] != 0x55 or data[1] != 0xAA:
        return None, "Sync Error"

    if data[2] != 0x0A:
        return None, "Byte Error"

    tire_position = data[3]

    pressure_kpa = (data[4] * 5.5) - 100
    pressure_bar = pressure_kpa / 100.0

    temperature = data[5] - 50
    status = data[6]
    battery = data[7] / 10.0

    calc = (
        data[0] ^ data[1] ^ data[2] ^
        data[3] ^ data[4] ^ data[5] ^
        data[6] ^ data[7] ^ data[8]
    )

    recv = data[9]

    if calc != recv:
        return None, "Checksum Error"

    txt = f"""
TIRE {tire_position}

Pressure : {pressure_kpa:.1f} KPA
           {pressure_bar:.2f} BAR

Temp     : {temperature} °C
Battery  : {battery:.1f} V

Leak     : {bool(status & 0x08)}
Low Volt : {bool(status & 0x10)}
NoSignal : {bool(status & 0x20)}
Low Pres : {bool(status & 0x02)}
HighPres : {bool(status & 0x04)}
HighTemp : {bool(status & 0x01)}
"""

    return tire_position, txt


# =========================
# UPDATE TIRE BOX
# =========================
def update_tire_box(tire, text):

    if tire in tire_boxes:
        box = tire_boxes[tire]
        box.delete("1.0", tk.END)
        box.insert(tk.END, text)


# =========================
# REFRESH PORT
# =========================
def refresh_ports():
    ports = serial.tools.list_ports.comports()
    plist = [p.device for p in ports]
    combo_port["values"] = plist

    if plist:
        combo_port.current(0)


# =========================
# CONNECT
# =========================
def connect_serial():
    global ser, running

    try:
        port = combo_port.get()
        baud = int(combo_baud.get())

        ser = serial.Serial(port, baud, timeout=1)
        running = True

        raw_monitor.insert(tk.END, f"CONNECTED {port} @ {baud}\n")

        threading.Thread(target=read_serial, daemon=True).start()

    except Exception as e:
        messagebox.showerror("ERROR", str(e))


# =========================
# DISCONNECT
# =========================
def disconnect_serial():
    global running, ser

    running = False

    if ser and ser.is_open:
        ser.close()

    raw_monitor.insert(tk.END, "DISCONNECTED\n")


# =========================
# READ SERIAL
# =========================
def read_serial():
    global running, ser

    while running:
        try:
            data = ser.read(10)

            if len(data) == 10:

                data_list = list(data)
                hex_data = " ".join(f"{b:02X}" for b in data_list)

                tire, parsed = parse_tire_data(data_list)

                raw_monitor.insert(tk.END, f"{hex_data}\n")
                raw_monitor.see(tk.END)

                if tire:
                    root.after(0, update_tire_box, tire, parsed)

        except:
            break


# =========================
# GUI
# =========================
root = tk.Tk()
root.title("TPMS 8 Tire Dashboard")
root.geometry("1000x800")

# top
top = tk.Frame(root)
top.pack(pady=10)

tk.Label(top, text="COM").grid(row=0, column=0)

combo_port = ttk.Combobox(top, width=10)
combo_port.grid(row=0, column=1)

tk.Label(top, text="BAUD").grid(row=0, column=2)

combo_baud = ttk.Combobox(
    top,
    values=["9600","19200","38400","57600","115200"],
    width=10
)
combo_baud.grid(row=0, column=3)
combo_baud.set("19200")

tk.Button(top, text="Refresh", command=refresh_ports).grid(row=0,column=4,padx=5)
tk.Button(top, text="Connect", bg="green", fg="white",
          command=connect_serial).grid(row=0,column=5,padx=5)
tk.Button(top, text="Disconnect", bg="red", fg="white",
          command=disconnect_serial).grid(row=0,column=6,padx=5)


# =========================
# 8 TIRE GRID
# =========================
grid_frame = tk.Frame(root)
grid_frame.pack()

for i in range(1, 9):
    frame = tk.LabelFrame(
        grid_frame,
        text=f"TIRE {i}",
        padx=5,
        pady=5
    )

    r = (i-1)//4
    c = (i-1)%4

    frame.grid(row=r, column=c, padx=10, pady=10)

    txt = tk.Text(
        frame,
        width=28,
        height=12,
        font=("Consolas", 9)
    )

    txt.pack()

    tire_boxes[i] = txt


# =========================
# RAW SERIAL
# =========================
tk.Label(root, text="RAW SERIAL").pack()

raw_monitor = scrolledtext.ScrolledText(
    root,
    width=120,
    height=10,
    font=("Consolas", 9)
)
raw_monitor.pack(pady=10)

refresh_ports()
root.mainloop()