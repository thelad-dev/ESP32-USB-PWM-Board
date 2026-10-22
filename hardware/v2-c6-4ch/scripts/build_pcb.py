#!/usr/bin/env python3
"""Build KiCad 6 PCB + Gerbers for ESP32-C3 4ch PWM/Tach board.

Run on a machine with KiCad 6 footprints installed:
  python3 build_pcb.py
"""

from __future__ import annotations

import os
import sys
import zipfile

sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew
from pcbnew import (
    B_Cu,
    B_Mask,
    B_SilkS,
    BOARD,
    Edge_Cuts,
    EXCELLON_WRITER,
    F_Cu,
    F_Mask,
    F_Paste,
    F_SilkS,
    FOOTPRINT,
    FromMM,
    FootprintLoad,
    LSET,
    NETINFO_ITEM,
    PAD,
    PCB_SHAPE,
    PCB_TEXT,
    PCB_TRACK,
    PCB_VIA,
    PLOT_CONTROLLER,
    PLOT_FORMAT_GERBER,
    SHAPE_T_SEGMENT,
    ZONE,
    ZONE_FILLER,
    wxPoint,
    wxSize,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KICAD_DIR = os.path.join(ROOT, "kicad")
FAB_DIR = os.path.join(ROOT, "fab")
FP_ROOT = "/usr/share/kicad/footprints"

BOARD_W = 90.0
BOARD_H = 70.0


def mm(x: float, y: float) -> wxPoint:
    return wxPoint(FromMM(x), FromMM(y))


def load_fp(lib: str, name: str) -> FOOTPRINT:
    path = os.path.join(FP_ROOT, lib)
    fp = FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError(f"missing footprint {lib}:{name}")
    return fp


def add_edge_rect(board: BOARD, w: float, h: float) -> None:
    pts = [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]
    for i in range(4):
        seg = PCB_SHAPE(board)
        seg.SetShape(SHAPE_T_SEGMENT)
        seg.SetLayer(Edge_Cuts)
        seg.SetStart(mm(*pts[i]))
        seg.SetEnd(mm(*pts[i + 1]))
        seg.SetWidth(FromMM(0.1))
        board.Add(seg)


def ensure_net(board: BOARD, name: str):
    existing = board.FindNet(name)
    if existing:
        return existing
    net = NETINFO_ITEM(board, name)
    board.Add(net)
    return board.FindNet(name)


def place(
    board: BOARD,
    lib: str,
    name: str,
    ref: str,
    value: str,
    x: float,
    y: float,
    rot_deg: float = 0.0,
) -> FOOTPRINT:
    fp = load_fp(lib, name)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(mm(x, y))
    if rot_deg:
        fp.SetOrientationDegrees(rot_deg)
    board.Add(fp)
    return fp


def set_pad_net(fp: FOOTPRINT, pad_name: str, net) -> PAD:
    pad = fp.FindPadByNumber(pad_name)
    if pad is None:
        raise RuntimeError(f"{fp.GetReference()} missing pad {pad_name}")
    pad.SetNet(net)
    return pad


def add_track(board: BOARD, x1, y1, x2, y2, width_mm, layer, net) -> None:
    t = PCB_TRACK(board)
    t.SetStart(mm(x1, y1))
    t.SetEnd(mm(x2, y2))
    t.SetWidth(FromMM(width_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    board.Add(t)


def add_via(board: BOARD, x, y, net, diameter=0.8, drill=0.4) -> None:
    v = PCB_VIA(board)
    v.SetPosition(mm(x, y))
    v.SetWidth(FromMM(diameter))
    v.SetDrill(FromMM(drill))
    v.SetNet(net)
    board.Add(v)


def add_silk(board: BOARD, text: str, x: float, y: float, size=1.2) -> None:
    t = PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(mm(x, y))
    t.SetTextSize(wxSize(FromMM(size), FromMM(size)))
    t.SetLayer(F_SilkS)
    board.Add(t)


def pad_xy(pad: PAD):
    p = pad.GetPosition()
    return p.x / 1e6, p.y / 1e6  # nm to mm in KiCad 6? Actually internal is nm
    # KiCad uses nanometers: FromMM(1)=1e6


def connect_pads(board, pad_a: PAD, pad_b: PAD, width_mm, layer, net, via_at=None):
    ax, ay = pad_a.GetPosition().x / 1e6, pad_a.GetPosition().y / 1e6
    bx, by = pad_b.GetPosition().x / 1e6, pad_b.GetPosition().y / 1e6
    if via_at is None:
        add_track(board, ax, ay, bx, by, width_mm, layer, net)
    else:
        vx, vy = via_at
        add_track(board, ax, ay, vx, vy, width_mm, layer, net)
        add_via(board, vx, vy, net)
        add_track(board, vx, vy, bx, by, width_mm, B_Cu if layer == F_Cu else F_Cu, net)


def fill_gnd_zone(board: BOARD, net) -> None:
    zone = ZONE(board)
    zone.SetLayerSet(LSET(F_Cu))
    zone.SetNet(net)
    zone.SetLocalClearance(FromMM(0.25))
    zone.SetMinThickness(FromMM(0.2))
    zone.SetPadConnection(1)  # thermal
    outline = zone.Outline()
    outline.NewOutline()
    margin = 0.5
    for x, y in [
        (margin, margin),
        (BOARD_W - margin, margin),
        (BOARD_W - margin, BOARD_H - margin),
        (margin, BOARD_H - margin),
    ]:
        outline.Append(FromMM(x), FromMM(y))
    board.Add(zone)


def build() -> str:
    os.makedirs(KICAD_DIR, exist_ok=True)
    os.makedirs(FAB_DIR, exist_ok=True)

    board = BOARD()
    add_edge_rect(board, BOARD_W, BOARD_H)
    add_silk(board, "ESP32-C6 PWM 4ch", 45, 3, 1.5)
    add_silk(board, "USB ->", 45, 6, 1.0)
    add_silk(board, "FAILSAFE: ESP missing => fans FULL", 45, 67, 1.0)
    add_silk(board, "C6 SuperMini only (not C3)", 45, 8.5, 0.9)

    # Nets
    gnd = ensure_net(board, "GND")
    p3v3 = ensure_net(board, "+3V3")
    p12 = ensure_net(board, "+12V")
    p12f = ensure_net(board, "+12V_F")
    temp = ensure_net(board, "TEMP_DQ")

    pwm_nets = [ensure_net(board, f"PWM{i}") for i in range(1, 5)]
    gate_nets = [ensure_net(board, f"GATE{i}") for i in range(1, 5)]
    fan_pwm_nets = [ensure_net(board, f"FAN{i}_PWM") for i in range(1, 5)]
    tach_nets = [ensure_net(board, f"TACH{i}") for i in range(1, 5)]
    tach_gpio_nets = [ensure_net(board, f"TACH{i}_GPIO") for i in range(1, 5)]

    # ESP32-C6 SuperMini: two 1x10 female, ~15.24 mm row pitch (board ~18 mm wide).
    # MakerGO / common C6 SuperMini (USB at top / -Y):
    # Left 1..10: GPIO16,17,0,1,2,3,4,5,6,7
    # Right 1..10: 5V, GND, 3V3, GPIO20,19,18,15,14,9,8
    # GPIO21 is a stamp pad (not on side headers) -> J_IO21.
    # Avoid strapping/LED/USB: 4-9, 12, 13, 15 for fan drive.
    esp_cx, esp_cy = 45.0, 20.0
    row_dx = 7.62
    j_left = place(
        board,
        "Connector_PinSocket_2.54mm.pretty",
        "PinSocket_1x10_P2.54mm_Vertical",
        "J_ESP_L",
        "Socket_1x10",
        esp_cx - row_dx,
        esp_cy,
        0,
    )
    j_right = place(
        board,
        "Connector_PinSocket_2.54mm.pretty",
        "PinSocket_1x10_P2.54mm_Vertical",
        "J_ESP_R",
        "Socket_1x10",
        esp_cx + row_dx,
        esp_cy,
        0,
    )

    # Module 5V stays unconnected on the carrier (USB powers the module).
    v5 = ensure_net(board, "MOD_5V_NC")
    set_pad_net(j_right, "1", v5)
    set_pad_net(j_right, "2", gnd)
    set_pad_net(j_right, "3", p3v3)
    # PWM on safe GPIOs 0..3 (left pads 3..6)
    set_pad_net(j_left, "3", pwm_nets[0])  # GPIO0
    set_pad_net(j_left, "4", pwm_nets[1])  # GPIO1
    set_pad_net(j_left, "5", pwm_nets[2])  # GPIO2
    set_pad_net(j_left, "6", pwm_nets[3])  # GPIO3
    # Tach on GPIO20,19,18,14 (right pads 4,5,6,8)
    set_pad_net(j_right, "4", tach_gpio_nets[0])  # GPIO20
    set_pad_net(j_right, "5", tach_gpio_nets[1])  # GPIO19
    set_pad_net(j_right, "6", tach_gpio_nets[2])  # GPIO18
    set_pad_net(j_right, "8", tach_gpio_nets[3])  # GPIO14

    # TEMP on GPIO21 stamp: single pin socket near module end
    j_io21 = place(
        board,
        "Connector_PinSocket_2.54mm.pretty",
        "PinSocket_1x01_P2.54mm_Vertical",
        "J_IO21",
        "Socket_1x01",
        esp_cx,
        esp_cy + 14.0,
        0,
    )
    set_pad_net(j_io21, "1", temp)
    add_silk(board, "IO21 TEMP", esp_cx, esp_cy + 17.5, 0.9)

    # Power input
    j_pwr = place(
        board,
        "TerminalBlock_Phoenix.pretty",
        "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
        "J_PWR",
        "KF128_5.08_2P",
        10,
        10,
        0,
    )
    set_pad_net(j_pwr, "1", p12)  # +12V
    set_pad_net(j_pwr, "2", gnd)
    add_silk(board, "+12V", 6, 6, 1.0)
    add_silk(board, "GND", 14, 6, 1.0)

    # PTC F1 between +12V and +12V_F
    f1 = place(board, "Fuse.pretty", "Fuse_1812_4532Metric", "F1", "PTC_3A_30V", 22, 10, 0)
    set_pad_net(f1, "1", p12)
    set_pad_net(f1, "2", p12f)

    # Reverse Schottky D_REV cathode to +12V_F, anode GND
    d_rev = place(board, "Diode_SMD.pretty", "D_SMA", "D_REV", "SS34", 30, 10, 0)
    set_pad_net(d_rev, "2", p12f)  # cathode (KiCad diode pad2 often K)
    set_pad_net(d_rev, "1", gnd)

    # TVS
    d_tvs = place(board, "Diode_SMD.pretty", "D_SMA", "D_TVS", "SMAJ15A", 38, 10, 0)
    set_pad_net(d_tvs, "2", p12f)
    set_pad_net(d_tvs, "1", gnd)

    # Bulk + decouple
    c_bulk = place(
        board, "Capacitor_SMD.pretty", "C_0805_2012Metric", "C_BULK", "10u", 46, 10, 0
    )
    set_pad_net(c_bulk, "1", p12f)
    set_pad_net(c_bulk, "2", gnd)

    c_dec = place(
        board, "Capacitor_SMD.pretty", "C_0603_1608Metric", "C_3V3", "100n", 54, 10, 0
    )
    set_pad_net(c_dec, "1", p3v3)
    set_pad_net(c_dec, "2", gnd)

    # DS18B20 + pullup
    u_temp = place(
        board, "Package_TO_SOT_THT.pretty", "TO-92", "U_TEMP", "DS18B20+", 80, 18, 0
    )
    # TO-92 KiCad: 1,2,3 — DS18B20 flat-facing: 1=GND 2=DQ 3=VDD
    set_pad_net(u_temp, "1", gnd)
    set_pad_net(u_temp, "2", temp)
    set_pad_net(u_temp, "3", p3v3)
    r_temp = place(
        board, "Resistor_SMD.pretty", "R_0603_1608Metric", "R_TEMP", "4.7k", 80, 26, 90
    )
    set_pad_net(r_temp, "1", p3v3)
    set_pad_net(r_temp, "2", temp)

    # Optional external probe header 1x3
    j_temp = place(
        board,
        "Connector_PinHeader_2.54mm.pretty",
        "PinHeader_1x03_P2.54mm_Vertical",
        "J_TEMP",
        "PROBE_1x3",
        80,
        36,
        0,
    )
    set_pad_net(j_temp, "1", gnd)
    set_pad_net(j_temp, "2", temp)
    set_pad_net(j_temp, "3", p3v3)
    add_silk(board, "TEMP", 80, 42, 1.0)

    # Four channels along bottom
    for i in range(4):
        cx = 12 + i * 20
        cy_fan = 58
        cy_q = 42
        cy_r = 34

        jfan = place(
            board,
            "Connector_PinHeader_2.54mm.pretty",
            "PinHeader_1x04_P2.54mm_Vertical",
            f"J_FAN{i+1}",
            "2510-4A",
            cx,
            cy_fan,
            0,
        )
        # Fan: 1=+12V 2=GND 3=TACH 4=PWM
        set_pad_net(jfan, "1", p12f)
        set_pad_net(jfan, "2", gnd)
        set_pad_net(jfan, "3", tach_nets[i])
        set_pad_net(jfan, "4", fan_pwm_nets[i])
        add_silk(board, f"FAN{i+1}", cx, 64, 1.0)

        q = place(
            board,
            "Package_TO_SOT_SMD.pretty",
            "SOT-23",
            f"Q{i+1}",
            "AO3400A",
            cx,
            cy_q,
            0,
        )
        # SOT-23 AO3400: 1=G 2=S 3=D
        set_pad_net(q, "1", gate_nets[i])
        set_pad_net(q, "2", gnd)
        set_pad_net(q, "3", fan_pwm_nets[i])

        r_series = place(
            board,
            "Resistor_SMD.pretty",
            "R_0603_1608Metric",
            f"R{i+1}A",
            "100",
            cx - 4,
            cy_r,
            0,
        )
        set_pad_net(r_series, "1", pwm_nets[i])
        set_pad_net(r_series, "2", gate_nets[i])

        r_pd = place(
            board,
            "Resistor_SMD.pretty",
            "R_0603_1608Metric",
            f"R{i+1}B",
            "100k",
            cx + 4,
            cy_r,
            0,
        )
        set_pad_net(r_pd, "1", gate_nets[i])
        set_pad_net(r_pd, "2", gnd)

        r_pu = place(
            board,
            "Resistor_SMD.pretty",
            "R_0603_1608Metric",
            f"R{i+1}C",
            "10k",
            cx - 4,
            cy_r - 6,
            0,
        )
        set_pad_net(r_pu, "1", p3v3)
        set_pad_net(r_pu, "2", tach_gpio_nets[i])

        r_ser_t = place(
            board,
            "Resistor_SMD.pretty",
            "R_0603_1608Metric",
            f"R{i+1}D",
            "1k",
            cx + 4,
            cy_r - 6,
            0,
        )
        set_pad_net(r_ser_t, "1", tach_nets[i])
        set_pad_net(r_ser_t, "2", tach_gpio_nets[i])

        d_cl = place(
            board,
            "Package_TO_SOT_SMD.pretty",
            "SOT-23",
            f"D{i+1}",
            "BAT54S",
            cx,
            cy_r - 12,
            0,
        )
        # BAT54S: use diode pin1(A)->pin3(C) as clamp to 3V3
        set_pad_net(d_cl, "1", tach_gpio_nets[i])
        set_pad_net(d_cl, "3", p3v3)
        # pin2 unused / tie to 3V3 via second diode ok
        set_pad_net(d_cl, "2", p3v3)

    # Manual short routes for critical power / ESP power
    # J_PWR.1 -> F1.1, F1.2 -> D_REV/TVS/C_BULK already net-tied; add pours + a few tracks
    connect_pads(board, j_pwr.FindPadByNumber("1"), f1.FindPadByNumber("1"), 0.6, F_Cu, p12)
    connect_pads(board, f1.FindPadByNumber("2"), d_rev.FindPadByNumber("2"), 0.6, F_Cu, p12f)
    connect_pads(board, d_rev.FindPadByNumber("2"), d_tvs.FindPadByNumber("2"), 0.6, F_Cu, p12f)
    connect_pads(board, d_tvs.FindPadByNumber("2"), c_bulk.FindPadByNumber("1"), 0.6, F_Cu, p12f)

    # Route each channel: series R and pulldown already pad-netted; add short tracks ESP->R
    for i in range(4):
        # find footprints by ref
        fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
        r_a = fps[f"R{i+1}A"]
        # PWM from ESP pads to R series: route via midpoints
        # Left pads 3..6 = GPIO0..3
        esp_pad = j_left.FindPadByNumber(str(3 + i))
        connect_pads(board, esp_pad, r_a.FindPadByNumber("1"), 0.25, F_Cu, pwm_nets[i])

        # Right: GPIO20,19,18,14 = pads 4,5,6,8
        tach_pad_num = ("4", "5", "6", "8")[i]
        tpad = j_right.FindPadByNumber(tach_pad_num)
        r_c = fps[f"R{i+1}C"]
        connect_pads(board, tpad, r_c.FindPadByNumber("2"), 0.25, F_Cu, tach_gpio_nets[i])

        # Fan PWM pad to Q drain (same net — short track if needed)
        q = fps[f"Q{i+1}"]
        jfan = fps[f"J_FAN{i+1}"]
        connect_pads(
            board, q.FindPadByNumber("3"), jfan.FindPadByNumber("4"), 0.3, F_Cu, fan_pwm_nets[i]
        )
        connect_pads(
            board, jfan.FindPadByNumber("3"), fps[f"R{i+1}D"].FindPadByNumber("1"), 0.25, F_Cu, tach_nets[i]
        )
        # +12V to fan
        connect_pads(board, c_bulk.FindPadByNumber("1"), jfan.FindPadByNumber("1"), 0.5, F_Cu, p12f)

    # Temp to ESP IO21 stamp socket
    connect_pads(board, j_io21.FindPadByNumber("1"), u_temp.FindPadByNumber("2"), 0.25, F_Cu, temp)
    connect_pads(board, r_temp.FindPadByNumber("2"), u_temp.FindPadByNumber("2"), 0.25, F_Cu, temp)

    # 3V3 from ESP socket (right pad 3) to pullups / sensor
    connect_pads(board, j_right.FindPadByNumber("3"), c_dec.FindPadByNumber("1"), 0.35, F_Cu, p3v3)
    connect_pads(board, c_dec.FindPadByNumber("1"), r_temp.FindPadByNumber("1"), 0.35, F_Cu, p3v3)

    # Explicit GND bus (no copper pour: ZONE_FILLER SIGSEGVs headless in KiCad 6.0.11)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    gnd_hub = j_pwr.FindPadByNumber("2")
    connect_pads(board, gnd_hub, j_right.FindPadByNumber("2"), 0.5, F_Cu, gnd)
    connect_pads(board, gnd_hub, d_rev.FindPadByNumber("1"), 0.5, F_Cu, gnd)
    connect_pads(board, gnd_hub, d_tvs.FindPadByNumber("1"), 0.5, F_Cu, gnd)
    connect_pads(board, gnd_hub, c_bulk.FindPadByNumber("2"), 0.5, F_Cu, gnd)
    connect_pads(board, gnd_hub, c_dec.FindPadByNumber("2"), 0.4, F_Cu, gnd)
    connect_pads(board, gnd_hub, u_temp.FindPadByNumber("1"), 0.4, F_Cu, gnd)
    connect_pads(board, gnd_hub, j_temp.FindPadByNumber("1"), 0.4, F_Cu, gnd)
    for i in range(4):
        connect_pads(
            board, gnd_hub, fps[f"J_FAN{i+1}"].FindPadByNumber("2"), 0.5, F_Cu, gnd
        )
        connect_pads(
            board, gnd_hub, fps[f"Q{i+1}"].FindPadByNumber("2"), 0.4, F_Cu, gnd
        )
        connect_pads(
            board, gnd_hub, fps[f"R{i+1}B"].FindPadByNumber("2"), 0.3, F_Cu, gnd
        )

    # 3V3 to channel tach pull-ups
    for i in range(4):
        connect_pads(
            board,
            c_dec.FindPadByNumber("1"),
            fps[f"R{i+1}C"].FindPadByNumber("1"),
            0.3,
            F_Cu,
            p3v3,
        )
        connect_pads(
            board,
            fps[f"R{i+1}A"].FindPadByNumber("2"),
            fps[f"Q{i+1}"].FindPadByNumber("1"),
            0.25,
            F_Cu,
            gate_nets[i],
        )
        connect_pads(
            board,
            fps[f"R{i+1}B"].FindPadByNumber("1"),
            fps[f"Q{i+1}"].FindPadByNumber("1"),
            0.25,
            F_Cu,
            gate_nets[i],
        )
        connect_pads(
            board,
            fps[f"R{i+1}D"].FindPadByNumber("2"),
            fps[f"R{i+1}C"].FindPadByNumber("2"),
            0.25,
            F_Cu,
            tach_gpio_nets[i],
        )
        connect_pads(
            board,
            fps[f"D{i+1}"].FindPadByNumber("1"),
            fps[f"R{i+1}C"].FindPadByNumber("2"),
            0.25,
            F_Cu,
            tach_gpio_nets[i],
        )
        connect_pads(
            board,
            fps[f"D{i+1}"].FindPadByNumber("3"),
            c_dec.FindPadByNumber("1"),
            0.25,
            F_Cu,
            p3v3,
        )

    pcb_path = os.path.join(KICAD_DIR, "esp32-c6-pwm-4ch.kicad_pcb")
    print("saving", pcb_path)
    pcbnew.SaveBoard(pcb_path, board)
    return pcb_path


def export_fab(pcb_path: str) -> str:
    board = pcbnew.LoadBoard(pcb_path)
    gerber_dir = os.path.join(FAB_DIR, "gerber")
    os.makedirs(gerber_dir, exist_ok=True)
    for f in os.listdir(gerber_dir):
        os.remove(os.path.join(gerber_dir, f))

    pctl = PLOT_CONTROLLER(board)
    popt = pctl.GetPlotOptions()
    popt.SetOutputDirectory(gerber_dir)
    popt.SetPlotFrameRef(False)
    popt.SetAutoScale(False)
    popt.SetScale(1)
    popt.SetMirror(False)
    popt.SetUseGerberAttributes(True)
    popt.SetUseGerberProtelExtensions(True)
    popt.SetExcludeEdgeLayer(True)
    popt.SetUseAuxOrigin(False)
    popt.SetSubtractMaskFromSilk(True)

    for suffix, layer, desc in [
        ("F_Cu", F_Cu, "Top copper"),
        ("B_Cu", B_Cu, "Bottom copper"),
        ("F_SilkS", F_SilkS, "Silk top"),
        ("B_SilkS", B_SilkS, "Silk bottom"),
        ("F_Mask", F_Mask, "Mask top"),
        ("B_Mask", B_Mask, "Mask bottom"),
        ("F_Paste", F_Paste, "Paste top"),
        ("Edge_Cuts", Edge_Cuts, "Edge"),
    ]:
        pctl.SetLayer(layer)
        pctl.OpenPlotfile(suffix, PLOT_FORMAT_GERBER, desc)
        pctl.PlotLayer()
    pctl.ClosePlot()

    drl = EXCELLON_WRITER(board)
    drl.SetOptions(False, False, wxPoint(0, 0), False)
    drl.SetFormat(True)
    drl.CreateDrillandMapFilesSet(gerber_dir, True, False)

    zip_path = os.path.join(FAB_DIR, "JLCPCB-gerbers-esp32-c6-pwm-4ch.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(os.listdir(gerber_dir)):
            zf.write(os.path.join(gerber_dir, name), name)
    return zip_path


def write_cpl(pcb_path: str) -> str:
    """JLCPCB-ish CPL for SMD parts only (THT hand-soldered)."""
    board = pcbnew.LoadBoard(pcb_path)
    smd_refs = set()
    for i in range(1, 5):
        smd_refs.update({f"Q{i}", f"R{i}A", f"R{i}B", f"R{i}C", f"R{i}D", f"D{i}"})
    smd_refs.update({"F1", "D_REV", "D_TVS", "C_BULK", "C_3V3", "R_TEMP"})

    # Designator, Val, Package, Mid X, Mid Y, Rotation, Layer
    rows = ["Designator,Val,Package,Mid X,Mid Y,Rotation,Layer"]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in smd_refs:
            continue
        x = fp.GetPosition().x / 1e6
        y = BOARD_H - (fp.GetPosition().y / 1e6)  # JLCPCB: bottom-left origin, Y up
        rot = fp.GetOrientationDegrees()
        rows.append(
            f"{ref},{fp.GetValue()},{fp.GetFPID().GetLibItemName()},{x:.4f},{y:.4f},{rot:.1f},Top"
        )
    path = os.path.join(FAB_DIR, "cpl-smd.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    return path


def main() -> None:
    pcb = build()
    z = export_fab(pcb)
    cpl = write_cpl(pcb)
    print("PCB", pcb)
    print("ZIP", z)
    print("CPL", cpl)


if __name__ == "__main__":
    main()
