#!/usr/bin/env python3
"""
OpenUtau-TTS-UTAU (frontend Qt): escribe texto -> .ustx -> openutau-render -> wav -> reproduce.
    pip install PySide6
    python loquendo_qt.py
Pon junto a este archivo openutau_tts.py. Configura en la pestaña la ruta del renderizador.
"""
import os, sys, json, subprocess, tempfile
from PySide6.QtCore import QUrl, QSettings, Qt, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
                               QLabel, QSlider, QLineEdit, QFileDialog, QFormLayout, QCheckBox, QMessageBox)
import openutau_tts as lq

def slider(lo, hi, val, escala=1):
    s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); return s

class Worker(QThread):
    listo = Signal(str); error = Signal(str)
    def __init__(self, cmd, wav): super().__init__(); self.cmd, self.wav = cmd, wav
    def run(self):
        try:
            p = subprocess.run(self.cmd, capture_output=True, text=True, timeout=600)
            if p.returncode == 0 and os.path.exists(self.wav): self.listo.emit(self.wav)
            else: self.error.emit((p.stdout + "\n" + p.stderr).strip() or "falló el renderizado")
        except Exception as e: self.error.emit(str(e))

class App(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("OpenUtau-TTS-UTAU"); self.cfg = QSettings("loquendo-utau", "app")
        v = QVBoxLayout(self)
        self.txt = QPlainTextEdit("Hola, esto es una prueba."); v.addWidget(self.txt)
        f = QFormLayout(); v.addLayout(f)
        self.tono = slider(36, 84, 60); self.vel = slider(5, 20, 10); self.pausa = slider(0, 20, 10)
        f.addRow("Tono (MIDI)", self.tono); f.addRow("Velocidad (x0.1)", self.vel); f.addRow("Pausas (x0.1)", self.pausa)
        self.render = QLineEdit(self.cfg.value("render", "dotnet run --project OpenUtau.Render -c Release --"))
        f.addRow("Comando renderizador", self.render)
        self.singer = QLineEdit(self.cfg.value("singer", lq.SINGER)); f.addRow("Cantante", self.singer)
        h = QHBoxLayout(); v.addLayout(h)
        self.b_gen = QPushButton("Hablar"); self.b_ustx = QPushButton("Solo .ustx"); self.b_save = QPushButton("Guardar wav…")
        for b in (self.b_gen, self.b_ustx, self.b_save): h.addWidget(b)
        self.estado = QLabel(""); v.addWidget(self.estado)
        self.player = QMediaPlayer(); self.out = QAudioOutput(); self.player.setAudioOutput(self.out)
        self.wav = None
        self.b_gen.clicked.connect(self.hablar); self.b_ustx.clicked.connect(self.solo_ustx); self.b_save.clicked.connect(self.guardar)

    def crear_ustx(self, ruta):
        lq.SINGER = self.singer.text().strip() or lq.SINGER
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(lq.generar_ustx(self.txt.toPlainText().strip(), self.tono.value(), self.vel.value()/10, self.pausa.value()/10))
        self.cfg.setValue("render", self.render.text()); self.cfg.setValue("singer", self.singer.text())

    def solo_ustx(self):
        r, _ = QFileDialog.getSaveFileName(self, "Guardar", "", "OpenUtau (*.ustx)")
        if r: self.crear_ustx(r); self.estado.setText("Creado " + r)

    def hablar(self):
        d = tempfile.mkdtemp(); u = os.path.join(d, "t.ustx"); self.wav = os.path.join(d, "t.wav")
        self.crear_ustx(u); self.estado.setText("Renderizando…"); self.b_gen.setEnabled(False)
        cmd = self.render.text().split() + [u, self.wav]
        self.w = Worker(cmd, self.wav); self.w.listo.connect(self.reproducir); self.w.error.connect(self.fallo); self.w.start()

    def reproducir(self, wav):
        self.b_gen.setEnabled(True); self.estado.setText("Listo")
        self.player.setSource(QUrl.fromLocalFile(wav)); self.out.setVolume(1.0); self.player.play()

    def fallo(self, msg):
        self.b_gen.setEnabled(True); self.estado.setText("Error"); QMessageBox.warning(self, "Error", msg[-1500:])

    def guardar(self):
        if not self.wav or not os.path.exists(self.wav): return
        r, _ = QFileDialog.getSaveFileName(self, "Guardar wav", "", "WAV (*.wav)")
        if r: import shutil; shutil.copy(self.wav, r)

if __name__ == "__main__":
    a = QApplication(sys.argv); w = App(); w.resize(520, 480); w.show(); sys.exit(a.exec())
