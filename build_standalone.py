#!/usr/bin/env python3
"""
build_standalone.py
-------------------
Génère une version autonome de navigation_periodes_athletes.html :
- JSX pré-compilé (Babel supprimé)
- React + ReactDOM intégrés
- Police Prompt (400 + 700) intégrée en base64
- Aucune dépendance externe — fonctionne sans internet, sur mobile et tablette

PRÉREQUIS (à installer une seule fois dans le terminal VS Code) :
    npm install -g @babel/core @babel/cli @babel/preset-react @babel/preset-env
    npm install @fontsource/prompt

UTILISATION :
    python3 build_standalone.py

RÉSULTAT :
    PDLTA.html  (même dossier)
"""

import os
import re
import base64
import subprocess
import sys
import tempfile

# ── Chemins ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE  = os.path.join(SCRIPT_DIR, "index.html")
OUTPUT_FILE  = os.path.join(SCRIPT_DIR, "PDLTA.html")
FONTSOURCE   = os.path.join(SCRIPT_DIR, "node_modules", "@fontsource", "prompt", "files")

# ── 1. Vérifications préalables ───────────────────────────────────────────────
print("── Vérification des prérequis ──")

if not os.path.exists(SOURCE_FILE):
    print(f"ERREUR : fichier source introuvable : {SOURCE_FILE}")
    sys.exit(1)

# Babel CLI
babel_cmd = None
for candidate in ["babel", os.path.expanduser("~/.npm-global/bin/babel")]:
    if subprocess.run(["which", candidate], capture_output=True).returncode == 0:
        babel_cmd = candidate
        break
if babel_cmd is None:
    print("ERREUR : babel CLI non trouvé.")
    print("  → Installez-le : npm install -g @babel/core @babel/cli @babel/preset-react @babel/preset-env")
    sys.exit(1)
print(f"  ✓ Babel : {babel_cmd}")

# React UMD (dans node_modules ou npm global)
react_candidates = [
    os.path.join(SCRIPT_DIR, "node_modules", "react", "umd", "react.production.min.js"),
]
react_path = next((p for p in react_candidates if os.path.exists(p)), None)
if react_path is None:
    print("ERREUR : react non trouvé dans node_modules.")
    print("  → Installez-le : npm install react@18 react-dom@18")
    sys.exit(1)
reactdom_path = react_path.replace("react/umd/react.", "react-dom/umd/react-dom.")
if not os.path.exists(reactdom_path):
    print(f"ERREUR : react-dom non trouvé : {reactdom_path}")
    sys.exit(1)
print(f"  ✓ React    : {react_path}")
print(f"  ✓ ReactDOM : {reactdom_path}")

# Fontsource Prompt
font_400 = os.path.join(FONTSOURCE, "prompt-latin-400-normal.woff2")
font_700 = os.path.join(FONTSOURCE, "prompt-latin-700-normal.woff2")
fonts_available = os.path.exists(font_400) and os.path.exists(font_700)
if not fonts_available:
    print("  ⚠ Police Prompt non trouvée — la police sera chargée depuis Google Fonts si connecté.")
    print("    → Pour l'intégrer : npm install @fontsource/prompt")
else:
    print(f"  ✓ Prompt 400 : {font_400}")
    print(f"  ✓ Prompt 700 : {font_700}")

# ── 2. Lecture du source ──────────────────────────────────────────────────────
print("\n── Lecture du fichier source ──")
with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    content = f.read()
print(f"  Taille : {len(content)/1024/1024:.2f} MB")

# ── 3. Extraction et compilation du JSX ───────────────────────────────────────
print("\n── Compilation du JSX ──")
start_tag = '<script type="text/babel">'
end_tag   = "</script>"
start_idx = content.index(start_tag) + len(start_tag)
end_idx   = content.rindex(end_tag)
jsx_code  = content[start_idx:end_idx]
print(f"  JSX extrait : {len(jsx_code)/1024:.0f} KB")

with tempfile.NamedTemporaryFile(suffix=".jsx", mode="w", encoding="utf-8", delete=False) as tmp_jsx:
    tmp_jsx.write(jsx_code)
    tmp_jsx_path = tmp_jsx.name

compiled_path = tmp_jsx_path.replace(".jsx", ".compiled.js")

result = subprocess.run(
    [babel_cmd, tmp_jsx_path,
     "--presets", "@babel/preset-react,@babel/preset-env",
     "--out-file", compiled_path],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"ERREUR Babel :\n{result.stderr}")
    sys.exit(1)

with open(compiled_path, "r", encoding="utf-8") as f:
    compiled_js = f.read()
print(f"  JS compilé  : {len(compiled_js)/1024:.0f} KB  ✓")

os.unlink(tmp_jsx_path)
os.unlink(compiled_path)

# ── 4. Chargement de React et ReactDOM ───────────────────────────────────────
print("\n── Chargement de React + ReactDOM ──")
with open(react_path, "r", encoding="utf-8") as f:
    react_js = f.read()
with open(reactdom_path, "r", encoding="utf-8") as f:
    reactdom_js = f.read()
print(f"  React    : {len(react_js)/1024:.0f} KB")
print(f"  ReactDOM : {len(reactdom_js)/1024:.0f} KB")

# ── 5. Police Prompt en base64 ────────────────────────────────────────────────
font_css = ""
if fonts_available:
    print("\n── Intégration de la police Prompt ──")
    for weight, path in [("400", font_400), ("700", font_700)]:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        font_css += (
            f"@font-face {{\n"
            f"  font-family: 'Prompt';\n"
            f"  font-style: normal;\n"
            f"  font-display: swap;\n"
            f"  font-weight: {weight};\n"
            f"  src: url('data:font/woff2;base64,{b64}') format('woff2');\n"
            f"}}\n"
        )
        print(f"  Prompt {weight} : {os.path.getsize(path)/1024:.1f} KB  ✓")

# ── 6. Assemblage du fichier final ────────────────────────────────────────────
print("\n── Assemblage du fichier standalone ──")
output = content

# Supprimer preconnect et lien Google Fonts
output = re.sub(
    r'\s*<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*\n'
    r'\s*<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*\n'
    r'\s*<link href="https://fonts\.googleapis\.com[^"]*" rel="stylesheet">\s*\n',
    "\n",
    output
)

# Insérer police inline juste après <head> (si disponible)
if font_css:
    output = output.replace("<head>\n", f"<head>\n<style>\n{font_css}</style>\n", 1)

# Remplacer React CDN
output = output.replace(
    '<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>',
    f"<script>{react_js}</script>"
)

# Remplacer ReactDOM CDN
output = output.replace(
    '<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>',
    f"<script>{reactdom_js}</script>"
)

# Supprimer Babel CDN
output = output.replace(
    '<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>',
    ""
)

# Remplacer le bloc JSX par le JS compilé
start_idx2 = output.index('<script type="text/babel">')
end_idx2   = output.rindex("</script>") + len("</script>")
output = output[:start_idx2] + f"<script>{compiled_js}</script>" + output[end_idx2:]

# ── 7. Vérifications finales ──────────────────────────────────────────────────
remaining_cdn = re.findall(r"https://(unpkg|fonts\.googleapis|cdnjs\.cloudflare)", output)
remaining_babel = output.count('type="text/babel"')
print(f"  CDN externes résiduels : {len(remaining_cdn)}")
print(f"  Balises text/babel     : {remaining_babel}")
if remaining_cdn or remaining_babel:
    print("  ⚠ Vérifier manuellement le fichier généré")

# ── 8. Écriture ───────────────────────────────────────────────────────────────
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(output)

print(f"\n── Terminé ──")
print(f"  Fichier source     : {len(content)/1024/1024:.2f} MB")
print(f"  Fichier standalone : {len(output)/1024/1024:.2f} MB")
print(f"  → {OUTPUT_FILE}")
