import tkinter as tk
from Router import RouterUnit, NetworkBackend

backend = NetworkBackend(dry_run=True)
routers = [RouterUnit(iface, lan_ports_quant=10) for iface in backend.get_interfaces()]

# --- UI Color Palette ---
BG_CANVAS        = "#808080"  # Medium grey rack background
BG_CHASSIS       = "#1e1e1e"  # Dark charcoal router unit housing
BG_PORT_HOUSING  = "#2b2f36"  # Gunmetal outer RJ45 cage
BG_PORT_RECESS   = "#1f2229"  # Dark recessed inner port face
BG_PORT_CAVITY   = "#0d0e11"  # Near-black RJ45 socket interior
BG_LED_HOUSING   = "#111317"  # Dark LED bezel

# Metallic Bevel Highlights & Shadows
METAL_LIGHT_TOP  = "#c4ccd4"  # Bright brushed-steel top edge
METAL_LIGHT_LEFT = "#aeb6bf"  # Silver-grey left edge
METAL_DARK_BOT   = "#141619"  # Deep shadow bottom edge
METAL_DARK_RIGHT = "#181b20"  # Dark iron right edge
METAL_TRIM       = "#5a626e"  # Mid-tone steel inner trim
SOCKET_OUTLINE   = "#6c7582"  # Light steel socket rim
LED_OUTLINE      = "#4a5058"  # Muted steel LED rim

# Port Accents, Pins & Status LEDs
ACCENT_WAN       = "#d97706"  # Amber / orange WAN stripe
ACCENT_LAN       = "#f3f4f6"  # Crisp off-white LAN stripe
GOLD_PIN         = "#d4af37"  # Metallic gold RJ45 contact pins
LED_ACTIVE       = "#00ff00"  # Bright green traffic LED
LED_OFF          = "#1a241a"  # Unlit dark LED

# Rocker Switch Colors
SWITCH_BEZEL       = "#111317"  # Dark plastic outer switch housing
SWITCH_RED_HIGH    = "#ef4444"  # Lit / raised crimson half
SWITCH_RED_MID     = "#b91c1c"  # Unlit raised red half
SWITCH_RED_SHADOW  = "#7f1d1d"  # Pressed-in dark red half
SWITCH_HIGHLIGHT   = "#fca5a5"  # Top edge specular highlight
SWITCH_CREASE      = "#3b0707"  # Center pivot divider line

SCALE = 1.25

def scale(val: float):

    return int(round(val * SCALE))

def truncate_text(text: str, max_len: int = 15) -> str:
    return text if len(text) <= max_len else text[:max_len -3] + "..."

def create_rocker_switch(parent_frame, initial_state=True, on_toggle=None):
    w, h = scale(38), scale(92)
    sw = tk.Canvas(parent_frame, width=w, height=h, background=SWITCH_BEZEL, highlightthickness=0, cursor="hand2")
    state = {"is_on": initial_state}

    def draw():
        sw.delete("all")
        mid_y = h // 2

        sw.create_rectangle(scale(1), scale(1), w - scale(2), h - scale(2),outline=METAL_TRIM, width=1)

        if state["is_on"]:
            print("Power switched on")
            top_fill = SWITCH_RED_HIGH
            bot_fill = SWITCH_RED_SHADOW

        else:
            print("Power switched off")
            top_fill = SWITCH_RED_SHADOW
            bot_fill = SWITCH_RED_HIGH


        # Top half (I) & Bottom half (O)
        sw.create_rectangle(scale(4), scale(4), w - scale(4), mid_y, fill=top_fill, outline="")
        sw.create_rectangle(scale(4), mid_y, w - scale(4), h - scale(4), fill=bot_fill, outline="")

        # 3D bevel highlights on whichever end is raised
        if state["is_on"]:
            sw.create_line(scale(4), scale(5), w - scale(4), scale(5), fill=SWITCH_HIGHLIGHT, width=2)
        else:
            sw.create_line(scale(4), h - scale(5), w - scale(4), h - scale(5), fill=SWITCH_RED_HIGH, width=2)

        # Crisp horizontal center pivot line separating I and O
        sw.create_line(scale(4), mid_y, w - scale(4), mid_y, fill=SWITCH_CREASE, width=max(2, scale(1)))

        # "I" and "O" markings centered on each half
        sw.create_text(w // 2, mid_y // 2 + scale(2), text="I", fill="white", font=("Ubuntu", scale(11), "bold"))
        sw.create_text(w // 2, mid_y + (mid_y // 2) - scale(1), text="O", fill="#e5e7eb",
                       font=("Consolas", scale(11), "bold"))

    def toggle(_event=None):
        state["is_on"] = not state["is_on"]
        draw()
        if on_toggle:
            on_toggle(state["is_on"])

    sw.bind("<Button-1>", toggle)
    draw()
    return sw, state

# WAN / LAN Jacks
# TODO: Assign actual portjack objects to ports

def create_rj45_canvas(parent_frame, accent_color=ACCENT_WAN, led_color="green"):
    port = tk.Canvas(parent_frame, width=scale(42), height=scale(42), bg="#2b2f36", highlightthickness=0)

    port.create_line(scale(1),scale(1),scale(41),scale(1), fill=METAL_LIGHT_TOP, width=2)
    port.create_line(scale(1),scale(1),scale(1),scale(41), fill=METAL_LIGHT_LEFT, width=2)
    port.create_line(scale(1),scale(41),scale(41),scale(41), fill=METAL_DARK_BOT, width=2)
    port.create_line(scale(41),scale(1),scale(41),scale(41), fill=METAL_DARK_RIGHT, width=2)

    port.create_rectangle(scale(3),scale(3),scale(39),scale(39), fill=BG_PORT_RECESS, outline=METAL_TRIM, width=1)
    port.create_line(scale(4),scale(4),scale(38),scale(4), fill=accent_color, width=2)

    port.create_rectangle(scale(5),scale(7),scale(12),scale(13), fill=BG_LED_HOUSING, outline=LED_OUTLINE)
    led_id = port.create_rectangle(scale(6),scale(8),scale(11),scale(12), fill=led_color, outline="")

    # Stepped RJ45 socket polygon (notched at top for clip)
    port.create_polygon(
        scale(8), scale(16), scale(15), scale(16), scale(15), scale(12), scale(27), scale(12), scale(27), scale(16), scale(34), scale(16), scale(34), scale(34), scale(8), scale(34),
        fill=BG_PORT_CAVITY, outline=SOCKET_OUTLINE
    )

    # 8 gold pins inside the bottom edge
    for pin in range(8):
        x = scale(10.5 + (pin * 3))
        port.create_line(x, scale(27), x, scale(33), fill=GOLD_PIN, width=1)

    return port, led_id

# MAIN WINDOW
window = tk.Tk()
window.configure(height=500, width=1500)

# main canvas
canvas = tk.Canvas(window, background="grey")
canvas.pack(fill="both", expand=True)

rack_frame = tk.Frame(canvas, bg=BG_CHASSIS, bd = 3, relief="sunken", padx=scale(10), pady=scale(8))


# ==== ISP MODEM CONSTRUCTION ====
isp_frame = tk.Frame(canvas, bg="#1e1e1e", bd=2, relief="groove")
isp_frame.configure(width=scale(50), height=scale(100))

isp_frame_label = tk.Label(isp_frame, text="ISP MODEM", font=("DejaVu Sans", scale(10), "bold italic"))
isp_frame_label.configure(anchor="w", background=BG_CHASSIS, foreground="white")
isp_frame_label.grid(row=0, column=0, padx=scale(5), pady=scale(5))

isp_ports = []
for i in range(10):
    port, led_id = create_rj45_canvas(isp_frame, accent_color=ACCENT_LAN, led_color=LED_ACTIVE)
    port.grid(row=i+1, column=0, padx=scale(5), pady=scale(5))
    isp_ports.append((port, led_id))

canvas.create_window(scale(10), scale(10), window=isp_frame, anchor="nw")

# ==== ROUTER UNIT CONSTRUCTION ====


for router in routers:

    iface = router.interface
    led_color = LED_ACTIVE if iface.is_up else LED_OFF

    unit_frame = tk.Frame(rack_frame, bg="#1e1e1e", bd=2, relief="groove")
    unit_frame.pack(side="top", fill="x", pady=scale(5))
    # TODO: Add interface name to unit frame label text
    # TODO: Loop through each interface and create a unit_frame for each

    name_str = truncate_text(iface.name, 15)
    ip_str = truncate_text(iface.ip_addr or "NO IP", 15)
    unit_frame_label = tk.Label(
        unit_frame,
        text=f"{router.interface.name}\n{router.interface.ip_addr or 'NO IP'}",
        width = 15,
        font=("DejaVu Sans",
              scale(10),
              "bold italic"),
        anchor="w",
        justify="left",
        background=BG_CHASSIS,
        foreground="white"
    )
    unit_frame_label.grid(row=0, column=0, columnspan=2, padx=scale(5), pady=scale(5), sticky="w")

    # TODO: make power button work
    power_switch, power_state = create_rocker_switch(unit_frame, initial_state=iface.is_up)
    power_switch.grid(row=1, column=0, rowspan=2, padx=scale(6), pady=scale(5))

    # Create 10 ports
    for idx, lan_port in enumerate(router.LAN_jacks):
        col = idx + 2

        port_entry = tk.Entry(unit_frame, width=4, font=("Consolas", scale(12)))
        port_entry.grid(row=0, column=col, padx=5, pady=5)
        lan_port.entry = port_entry

        wan_port, wan_led_id = create_rj45_canvas(unit_frame, accent_color=ACCENT_WAN, led_color=led_color)
        wan_port.grid(row=1, column=col, padx=5, pady=5)
        wan_port.grid_propagate(False)

        # Traffic blinkers
        # TODO: make the blinker work, change from black to green when traffic is flowing

        lan_port, lan_led_id = create_rj45_canvas(unit_frame, accent_color=ACCENT_LAN, led_color=led_color)
        lan_port.grid(row=2, column=col, padx=5, pady=5)
        lan_port.grid_propagate(False)


# MAINLOOP
window.update_idletasks()  # Forces Tkinter to calculate isp_frame's real width
isp_right_edge = scale(10) + isp_frame.winfo_width()
canvas.create_window(isp_right_edge + scale(35), scale(10), window=rack_frame, anchor="nw")

window.mainloop()