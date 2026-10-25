
#!/usr/bin/env bash
# Instala OpenUtau-TTS en ~/.local (sin root).
# Uso:  bash install.sh [ruta/al/repo/OpenUtau]      (por defecto ./OpenUtau)
# Desinstalar:  rm -rf ~/.local/share/openutau-tts ~/.local/bin/openutau-tts ~/.local/share/applications/openutau-tts.desktop
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
REPO="$(realpath "${1:-$AQUI/OpenUtau}")"
DEST="$HOME/.local/share/openutau-tts"

command -v dotnet >/dev/null || { echo "Falta dotnet (sudo pacman -S dotnet-sdk)"; exit 1; }
python3 -c "import PySide6" 2>/dev/null || { echo "Falta PySide6 (sudo pacman -S pyside6)"; exit 1; }
[ -d "$REPO/OpenUtau.Core" ] || { echo "No encuentro el repo de OpenUtau en $REPO"; exit 1; }

# El proyecto del renderizador debe estar dentro del repo
#
if [ ! -d "$REPO/OpenUtau.Render" ]; then
  mkdir -p "$REPO/OpenUtau.Render"
  cp "$REPO/OpenUtau.Render/"* "$REPO/OpenUtau.Render/"
fi


# cp "$AQUI/OpenUtau.Render/"* "$REPO/OpenUtau.Render/"   # asegura la versión más reciente

echo ">> Compilando el renderizador (una sola vez)..."
mkdir -p "$DEST/render" "$DEST/app"
dotnet publish "$REPO/OpenUtau.Render" -c Release -o "$DEST/render" 2>&1 | grep -v "warning NU" | tail -3
# por si el publish no copió el motor nativo
[ -f "$DEST/render/libworldline.so" ] || cp "$REPO/runtimes/linux-x64/native/libworldline.so" "$DEST/render/"

cp "$AQUI/openutau_tts.py" "$AQUI/openutau_tts_qt.py" "$DEST/app/"

mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
cat > "$HOME/.local/bin/openutau-tts" << LANZ
#!/usr/bin/env bash
export OPENUTAU_RENDER="dotnet $DEST/render/OpenUtau.Render.dll"
cd "$DEST/app"
exec python3 openutau_tts_qt.py "\$@"
LANZ
chmod +x "$HOME/.local/bin/openutau-tts"

cat > "$HOME/.local/share/applications/openutau-tts.desktop" << DESK
[Desktop Entry]
Type=Application
Name=OpenUtau-TTS
Comment=Texto a voz con OpenUtau
Exec=$HOME/.local/bin/openutau-tts
Terminal=false
Categories=AudioVideo;Audio;
DESK

echo ">> Listo. Ejecuta:  openutau-tts   (asegúrate de que ~/.local/bin esté en tu PATH)"
