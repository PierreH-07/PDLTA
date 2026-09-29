#!/usr/bin/env python3
"""
build_standalone.py
-------------------
Génère index.html (version publiée, GitHub Pages) à partir de index_avant_compile.html (qui reste LA source à modifier) :
- JSX pré-compilé (plus de Babel dans le navigateur)
- React, ReactDOM et Chart.js intégrés dans le fichier
- Police Prompt (400, 500, 600, 700 et 400 italique, comme ffnatation.fr) intégrée en base64
- Aucune dépendance externe : seuls index.html + le dossier images/ sont nécessaires

PRÉREQUIS (une seule fois, dans le dossier du projet) :
    npm install

UTILISATION :
    python3 build_standalone.py

RÉSULTAT :
    index.html  (même dossier, à côté de images/)
"""

import base64
import os
import re
import subprocess
import sys
import tempfile

# ── Chemins ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(SCRIPT_DIR, "index_avant_compile.html")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "index.html")
NODE_MODULES = os.path.join(SCRIPT_DIR, "node_modules")

BABEL_BIN = os.path.join(NODE_MODULES, ".bin", "babel")
LIBS = {
    "react":    os.path.join(NODE_MODULES, "react", "umd", "react.production.min.js"),
    "reactdom": os.path.join(NODE_MODULES, "react-dom", "umd", "react-dom.production.min.js"),
    "chartjs":  os.path.join(NODE_MODULES, "chart.js", "dist", "chart.umd.min.js"),
}
FONT_FACES = [("400", "normal"), ("500", "normal"), ("600", "normal"), ("700", "normal"), ("400", "italic")]  # mêmes graisses que le site ffnatation.fr
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
        fail(f"balise introuvable dans index_avant_compile.html : {label}")
    return new_text


# ── 1. Vérifications ─────────────────────────────────────────────────────────
print("── Vérification des prérequis ──")
if not os.path.exists(SOURCE_FILE):
    fail(f"fichier source introuvable : {SOURCE_FILE}")
missing = [p for p in [BABEL_BIN, *LIBS.values()] if not os.path.exists(p)]
missing += [os.path.join(FONT_DIR, f"prompt-latin-{w}-{st}.woff2") for w, st in FONT_FACES
            if not os.path.exists(os.path.join(FONT_DIR, f"prompt-latin-{w}-{st}.woff2"))]
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
    # preset-react : JSX ; preset-env : syntaxe récente (?. ??) convertie pour les
    # navigateurs listés dans package.json > browserslist (dont Safari/iOS 12+)
    result = subprocess.run(
        [BABEL_BIN, src, "--no-babelrc", "--presets", "@babel/preset-react,@babel/preset-env",
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
for w, st in FONT_FACES:
    with open(os.path.join(FONT_DIR, f"prompt-latin-{w}-{st}.woff2"), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    font_css += (f"@font-face{{font-family:'Prompt';font-style:{st};font-display:swap;"
                 f"font-weight:{w};src:url(data:font/woff2;base64,{b64}) format('woff2');}}\n")
output = output.replace("<head>", f"<head>\n<style>\n{font_css}</style>", 1)
print(f"  ✓ Graisses {', '.join(w + (' italique' if st == 'italic' else '') for w, st in FONT_FACES)}")

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
print("  À déployer : index.html + dossier images/")
