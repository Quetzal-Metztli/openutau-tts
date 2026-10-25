#!/usr/bin/env python3
"""
OpenUtau-TTS-UTAU: texto -> proyecto .ustx de OpenUtau (una nota por sílaba).

Uso (consola):
    python loquendo_utau.py "Hola, esto es una prueba" -o salida.ustx --tono 60 --velocidad 1.0
Uso (ventana):
    python loquendo_utau.py

Luego abre el .ustx en OpenUtau y exporta: Archivo > Exportar audio.
Requiere solo Python 3.8+ (tkinter viene incluido en la mayoría de instalaciones).
"""
import argparse, re, sys, os, subprocess, platform

# ------------------------- Configuración del cantante -------------------------
SINGER = "VozPorDefecto"
PHONEMIZER = "OpenUtau.Plugin.Builtin.EStoJAPhonemizer"
RENDERER = "WORLDLINE-R"
TICKS_BEAT = 480          # resolución de OpenUtau
BPM = 120                 # 1 beat = 0.5 s

# ------------------------------ Silabeo español -------------------------------
VOW_FUERTES = "aeoáéóàèò"
VOW_DEBILES = "iuíúü"
VOWELS = VOW_FUERTES + VOW_DEBILES
INSEPARABLES = {"pr","pl","br","bl","fr","fl","tr","dr","cr","cl","gr","gl","kr","kl","ch","ll","rr"}

def _es_vocal(c): return c.lower() in VOWELS

def silabear_palabra(w):
    w = w.lower()
    # núcleos vocálicos (agrupa diptongos/triptongos)
    n = len(w); i = 0; nucleos = []
    while i < n:
        if _es_vocal(w[i]):
            j = i
            while j + 1 < n and _es_vocal(w[j+1]):
                a, b = w[j], w[j+1]
                tilde_debil = a in "íú" or b in "íú"
                ambas_fuertes = a in VOW_FUERTES and b in VOW_FUERTES
                if tilde_debil or ambas_fuertes:  # hiato
                    break
                j += 1
            nucleos.append((i, j)); i = j + 1
        else:
            i += 1
    if not nucleos:
        return [w]
    cortes = []
    for (a1, b1), (a2, b2) in zip(nucleos, nucleos[1:]):
        cons = w[b1+1:a2]
        if len(cons) <= 1:
            corte = a2 - len(cons)                  # V-CV o hiato
        elif len(cons) == 2:
            corte = a2 - 2 if cons in INSEPARABLES else a2 - 1
        else:
            corte = a2 - 2 if cons[-2:] in INSEPARABLES else a2 - 1
        cortes.append(corte)
    sil, prev = [], 0
    for c in cortes:
        sil.append(w[prev:c]); prev = c
    sil.append(w[prev:])
    return [s for s in sil if s]

LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

def texto_a_notas(texto, velocidad=1.0, pausa=1.0):
    """Devuelve lista de (lyric|None, ticks). None = silencio.
    Una palabra con guiones ("pru-e-ba") se respeta tal cual, sin silabeo automático."""
    base = 190 / velocidad
    items = []
    for tok in re.findall(rf"[{LETRAS}]+(?:-[{LETRAS}]+)*|[,.;:!?¡¿\n]", texto):
        if re.match(rf"[{LETRAS}]", tok):
            sils = tok.lower().split("-") if "-" in tok else silabear_palabra(tok)
            for sl in sils:
                # sílabas largas (más fonemas) necesitan más tiempo para pronunciarse
                items.append((sl, int(base * (0.7 + 0.2 * len(sl)))))
            items.append((None, int(60 * pausa / velocidad)))
        elif tok in ",;:":
            items.append((None, int(240 * pausa / velocidad)))
        else:
            items.append((None, int(480 * pausa / velocidad)))
    return items

# ------------------------------- Generar .ustx --------------------------------
def generar_ustx(texto, tono=60, velocidad=1.0, pausa=1.0, plantilla=None):
    cab = None
    if plantilla and os.path.exists(plantilla):
        with open(plantilla, encoding="utf-8-sig") as f:
            raw = f.read()
        cab = raw.split("\ntracks:")[0]          # conserva 'expressions' del proyecto del usuario
    if cab is None:
        cab = f'name: OpenUtau-TTS\ncomment: ""\noutput_dir: Vocal\ncache_dir: UCache\nustx_version: "0.10"\nbpm: {BPM}\nbeat_per_bar: 4\nbeat_unit: 4\nexpressions: {{}}'
    out = [cab.rstrip(), "tracks:", f"- singer: {SINGER}", f"  phonemizer: {PHONEMIZER}",
           "  renderer_settings:", f"    renderer: {RENDERER}",
           "  track_name: Voz", "  track_color: Blue", "  mute: false", "  solo: false",
           "  volume: 0", "  pan: 0", "  track_expressions: []", "  voice_color_names:", '  - ""']
    notas, pos = [], 0
    for lyric, dur in texto_a_notas(texto, velocidad, pausa):
        if lyric is not None:
            notas.append(
f"""  - position: {pos}
    duration: {dur}
    tone: {tono}
    lyric: {lyric}
    pitch:
      data:
      - {{x: -40, y: 0, shape: io}}
      - {{x: 40, y: 0, shape: io}}
      snap_first: true
    vibrato: {{length: 0, period: 175, depth: 25, in: 10, out: 10, shift: 0, drift: 0, vol_link: 0}}
    tuning: 0
    phoneme_expressions: []
    phoneme_overrides: []""")
        pos += dur
    total = ((pos // 1920) + 1) * 1920
    out += ["voice_parts:", f"- duration: {total}", "  name: Texto", '  comment: ""', "  track_no: 0",
            "  position: 0", "  notes:"] + notas + ["  curves: []", "  masked_curves: []", "wave_parts: []", ""]
    return "\n".join(out)

# ----------------------------------- GUI --------------------------------------
def abrir(ruta):
    if platform.system() == "Windows": os.startfile(ruta)
    elif platform.system() == "Darwin": subprocess.Popen(["open", ruta])
    else: subprocess.Popen(["xdg-open", ruta])

def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    r = tk.Tk(); r.title("OpenUtau-TTS-UTAU")
    t = tk.Text(r, width=60, height=8); t.pack(padx=8, pady=8); t.insert("1.0", "Hola, esto es una prueba.")
    def esc(nombre, ini, fin, res, val):
        s = tk.Scale(r, label=nombre, from_=ini, to=fin, resolution=res, orient="horizontal", length=360)
        s.set(val); s.pack(); return s
    tono = esc("Tono (MIDI, 60 = Do central)", 36, 84, 1, 60)
    vel  = esc("Velocidad", 0.5, 2.0, 0.1, 1.0)
    pau  = esc("Pausas", 0.0, 2.0, 0.1, 1.0)
    def crear():
        ruta = filedialog.asksaveasfilename(defaultextension=".ustx", filetypes=[("OpenUtau", "*.ustx")])
        if not ruta: return
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(generar_ustx(t.get("1.0", "end").strip(), int(tono.get()), vel.get(), pau.get()))
        if messagebox.askyesno("Listo", "Proyecto creado. ¿Abrirlo en OpenUtau?"): abrir(ruta)
    tk.Button(r, text="Generar .ustx", command=crear).pack(pady=8)
    r.mainloop()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("texto", nargs="?"); ap.add_argument("-o", "--salida", default="salida.ustx")
    ap.add_argument("--tono", type=int, default=60); ap.add_argument("--velocidad", type=float, default=1.0)
    ap.add_argument("--pausa", type=float, default=1.0); ap.add_argument("--plantilla")
    a = ap.parse_args()
    if a.texto is None: gui(); sys.exit()
    with open(a.salida, "w", encoding="utf-8") as f:
        f.write(generar_ustx(a.texto, a.tono, a.velocidad, a.pausa, a.plantilla))
    print("Creado", a.salida)
