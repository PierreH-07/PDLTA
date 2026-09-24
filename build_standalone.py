#!/usr/bin/env python3
"""
build_standalone.py
-------------------
Génère index_compile.html à partir de index.html (qui reste LA source à modifier) :
- JSX pré-compilé (plus de Babel dans le navigateur)
- React, ReactDOM et Chart.js intégrés dans le fichier
- Police Prompt (300, 400, 600, 700) intégrée en base64
- Aucune dépendance externe : seuls index_compile.html + le dossier Images/ sont nécessaires

PRÉREQUIS (une seule fois, dans le dossier du projet) :
    npm install

UTILISATION :
    python3 build_standalone.py

RÉSULTAT :
    index_compile.html  (même dossier, à côté de Images/)
"""

import base64
import os
import re
import subprocess
import sys
import tempfile

# ── Chemins ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(SCRIPT_DIR, "index.html")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "index_compile.html")
NODE_MODULES = os.path.join(SCRIPT_DIR, "node_modules")

BABEL_BIN = os.path.join(NODE_MODULES, ".bin", "babel")
LIBS = {
    "react":    os.path.join(NODE_MODULES, "react", "umd", "react.production.min.js"),
    "reactdom": os.path.join(NODE_MODULES, "react-dom", "umd", "react-dom.production.min.js"),
    "chartjs":  os.path.join(NODE_MODULES, "chart.js", "dist", "chart.umd.min.js"),
}
FONT_WEIGHTS = ["300", "400", "600", "700"]  # mêmes graisses que le lien Google Fonts de index.html
FONT_DIR = os.path.join(NODE_MODULES, "@fontsource", "prompt", "files")


def fail(msg):
    print(f"ERREUR : {msg}")
    sys.exit(1)


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def inline_script(js):
    # Empêche le navigateur de fermer la balise <script> trop tôt
    return "<script>" + js.replace("</script", "<\\/script") + "</script>"


def replace_once(pattern, repl, text, label):
    new_text, n = re.subn(pattern, lambda m: repl, text, count=1)
    if n != 1:
        fail(f"balise introuvable dans index.html : {label}")
    return new_text


# ── 1. Vérifications ─────────────────────────────────────────────────────────
print("── Vérification des prérequis ──")
if not os.path.exists(SOURCE_FILE):
    fail(f"fichier source introuvable : {SOURCE_FILE}")
missing = [p for p in [BABEL_BIN, *LIBS.values()] if not os.path.exists(p)]
missing += [os.path.join(FONT_DIR, f"prompt-latin-{w}-normal.woff2") for w in FONT_WEIGHTS
            if not os.path.exists(os.path.join(FONT_DIR, f"prompt-latin-{w}-normal.woff2"))]
if missing:
    print("Fichiers manquants :")
    for p in missing:
        print("  -", os.path.relpath(p, SCRIPT_DIR))
    fail("lancez d'abord : npm install")
print("  ✓ Babel, React, ReactDOM, Chart.js, police Prompt")

content = read(SOURCE_FILE)
print(f"  Source : {len(content)/1024/1024:.2f} MB")

# ── 2. Compilation du JSX ────────────────────────────────────────────────────
print("\n── Compilation du JSX ──")
start_tag = '<script type="text/babel">'
if content.count(start_tag) != 1:
    fail('il doit y avoir exactement une balise <script type="text/babel">')
start = content.index(start_tag)
end = content.index("</script>", start) + len("</script>")
jsx_code = content[start + len(start_tag):end - len("</script>")]

with tempfile.TemporaryDirectory() as tmp:
    src, out = os.path.join(tmp, "app.jsx"), os.path.join(tmp, "app.js")
    with open(src, "w", encoding="utf-8") as f:
        f.write(jsx_code)
    # preset-react seul : le JSX est converti, le reste du code est laissé tel quel
    result = subprocess.run(
        [BABEL_BIN, src, "--no-babelrc", "--presets", "@babel/preset-react",
         "--out-file", out],
        capture_output=True, text=True, cwd=SCRIPT_DIR,
    )
    if result.returncode != 0:
        fail(f"Babel :\n{result.stderr}")
    compiled_js = read(out)
print(f"  JSX {len(jsx_code)/1024:.0f} KB → JS {len(compiled_js)/1024:.0f} KB  ✓")

output = content[:start] + inline_script(compiled_js) + content[end:]

# ── 3. Bibliothèques intégrées (remplace les appels CDN) ─────────────────────
print("\n── Intégration des bibliothèques ──")
output = replace_once(r'<script[^>]*src="https://unpkg\.com/react@[^"]*"[^>]*></script>',
                      inline_script(read(LIBS["react"])), output, "React")
output = replace_once(r'<script[^>]*src="https://unpkg\.com/react-dom@[^"]*"[^>]*></script>',
                      inline_script(read(LIBS["reactdom"])), output, "ReactDOM")
output = replace_once(r'<script[^>]*src="https://cdn\.jsdelivr\.net/npm/chart\.js@[^"]*"[^>]*></script>',
                      inline_script(read(LIBS["chartjs"])), output, "Chart.js")
output = replace_once(r'[ \t]*<script[^>]*src="https://unpkg\.com/@babel/standalone[^"]*"[^>]*></script>\n?',
                      "", output, "Babel")
print("  ✓ React, ReactDOM, Chart.js intégrés ; Babel retiré")

# ── 4. Police Prompt ─────────────────────────────────────────────────────────
print("\n── Intégration de la police Prompt ──")
output = re.sub(r'[ \t]*<link[^>]*href="https://fonts\.(googleapis|gstatic)\.com[^"]*"[^>]*>\n?', "", output)
font_css = ""
for w in FONT_WEIGHTS:
    with open(os.path.join(FONT_DIR, f"prompt-latin-{w}-normal.woff2"), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    font_css += ("@font-face{font-family:'Prompt';font-style:normal;font-display:swap;"
                 f"font-weight:{w};src:url(data:font/woff2;base64,{b64}) format('woff2');}}\n")
output = output.replace("<head>", f"<head>\n<style>\n{font_css}</style>", 1)
print(f"  ✓ Graisses {', '.join(FONT_WEIGHTS)}")

# ── 5. Contrôles ─────────────────────────────────────────────────────────────
print("\n── Contrôles ──")
external = re.findall(r'<(?:script|link)[^>]*(?:src|href)="https?://[^"]*"', output)
babel_left = output.count('type="text/babel"')
print(f"  Scripts/styles externes restants : {len(external)}")
print(f"  Balises text/babel restantes     : {babel_left}")
if external or babel_left:
    fail("le fichier compilé dépend encore de ressources externes")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(output)

print("\n── Terminé ──")
print(f"  → {os.path.relpath(OUTPUT_FILE, SCRIPT_DIR)} ({len(output)/1024/1024:.2f} MB)")
print("  À déployer : index_compile.html (renommé index.html si besoin) + dossier Images/")
