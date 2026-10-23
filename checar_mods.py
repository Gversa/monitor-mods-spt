import json, os, html, requests
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

URL = "https://sp-mod.com/mods"
ARQ = Path("vistos.json")
PAGINA = Path("docs/index.html")
TOPIC = os.environ.get("NTFY_TOPIC")


def pegar_mods():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    mods = {}
    for a in soup.find_all("a", href=True):
        h3 = a.find("h3")
        if h3 and h3.find("span"):
            mods[urljoin(URL, a["href"])] = h3.find("span").get_text(strip=True)
    if not mods:
        raise SystemExit("Nenhum mod encontrado: o layout do site pode ter mudado")
    return mods


dados = json.loads(ARQ.read_text()) if ARQ.exists() else {"mods": {}, "novos": []}
atuais = pegar_mods()
agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
primeira = not dados["mods"]
novos_agora = []

for link, titulo in atuais.items():
    if link not in dados["mods"]:
        dados["mods"][link] = titulo
        if not primeira:
            n = {"titulo": titulo, "link": link, "data": agora}
            dados["novos"].insert(0, n)
            novos_agora.append(n)

dados["novos"] = dados["novos"][:50]
dados["ultima_checagem"] = agora
ARQ.write_text(json.dumps(dados, ensure_ascii=False, indent=1))

itens = "".join(
    f'<li><a href="{html.escape(n["link"])}">{html.escape(n["titulo"])}</a>'
    f'<br><small>{n["data"]}</small></li>'
    for n in dados["novos"]
) or "<li>Nenhum mod novo desde que o monitor começou.</li>"

PAGINA.parent.mkdir(exist_ok=True)
PAGINA.write_text(f"""<!doctype html><html lang="pt-br"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Novos mods SPT</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:auto;padding:16px}}
li{{margin:12px 0}}</style></head><body>
<h2>Novos mods</h2><p>Última checagem: {agora}</p><ul>{itens}</ul></body></html>""")

if novos_agora and TOPIC:
    texto = "\n".join(f'{n["titulo"]}: {n["link"]}' for n in novos_agora)
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=texto.encode("utf-8"),
        headers={"Title": f"{len(novos_agora)} novo(s) mod(s)"},
    )