"""Camada de estilo do dashboard Minha_vida.

Centraliza o CSS dark (cards, headings de seção com barra lateral e boxes de KPI)
e helpers de renderização, seguindo o padrão visual dos projetos do Diogo
(referência: portifolio_diogo/utils/styles.py). Fonte única de aparência para as
3 páginas - evita duplicar CSS/HTML em cada uma.
"""
import streamlit as st

ACCENT = "#18990b"        # verde da identidade do projeto
ACCENT_SOFT = "#65B581"
DOWN = "#e06666"          # vermelho de tendência de queda (casa com .sub.down)

_CSS = """
<style>
/* ---- HEADING DE SEÇÃO (barra lateral verde) ---- */
.mv-sec {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f0f0f0;
    padding-left: 12px;
    border-left: 4px solid #18990b;
    margin: 4px 0 14px;
    line-height: 1.3;
}

/* ---- LINHA DE KPIs ---- */
.mv-kpis {
    display: grid;
    grid-template-columns: repeat(var(--mv-cols, 4), 1fr);
    gap: 14px;
    margin-bottom: 6px;
}

.mv-kpi {
    background: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 12px;
    padding: 18px 16px;
    text-align: center;
}

.mv-kpi .val {
    font-size: 1.9rem;
    font-weight: 800;
    color: #18990b;
    line-height: 1.1;
}

.mv-kpi .lbl {
    color: #9ca3af;
    font-size: 0.8rem;
    margin-top: 6px;
    font-weight: 500;
}

.mv-kpi .sub { font-size: 0.78rem; margin-top: 4px; font-weight: 600; }
.mv-kpi .sub.up { color: #65B581; }
.mv-kpi .sub.down { color: #e06666; }
.mv-kpi .sub.flat { color: #6b7280; }

/* mini timeline (sparkline) semanal dentro do box */
.mv-kpi .mv-spark { width: 100%; height: 34px; margin-top: 8px; display: block; }

footer { visibility: hidden; }
</style>
"""


def inject_css():
    """Injeta o CSS global do dashboard. Chamar uma vez por página."""
    st.markdown(_CSS, unsafe_allow_html=True)


def cabecalho_secao(titulo: str):
    """Renderiza um heading de seção com barra lateral verde."""
    st.markdown(f'<div class="mv-sec">{titulo}</div>', unsafe_allow_html=True)


def _fmt_valor(v):
    """Formata um ponto da série p/ o tooltip: fração vira %, resto 1 casa."""
    return f"{v:.0%}" if abs(v) <= 1.5 else f"{v:.1f}"


def _sparkline_svg(serie, cor=ACCENT, w=120, h=34, rotulo="Semanal", janela=12):
    """Mini timeline (área) como SVG inline, para caber dentro do box de KPI.

    serie: iterável de números (ex.: aderência/humor semanal). NaN é ignorado.
    cor: cor da linha/ponto (default verde; o box escolhe pela tendência).
    rotulo: prefixo do tooltip nativo (<title>) exibido ao passar o mouse.
    janela: nº de semanas mais recentes a exibir (declutter). None = tudo.
    Desenha ainda a linha de média (tracejada) da janela como referência.
    Retorna '' se houver menos de 2 pontos válidos.
    """
    pts = []
    for v in serie or []:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f:  # descarta NaN
            pts.append(f)
    total = len(pts)
    if janela:
        pts = pts[-janela:]  # só as últimas N semanas
    if len(pts) < 2:
        return ""

    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    n = len(pts)
    media = sum(pts) / n

    def _y(v):
        return h - ((v - lo) / rng) * (h - 6) - 3

    xs = [i / (n - 1) * w for i in range(n)]
    ys = [_y(v) for v in pts]
    my = _y(media)  # y da linha de média

    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"0,{h} " + linha + f" {w},{h}"

    lx, ly = xs[-1], ys[-1]  # ponto da última semana (destacado)

    # Tooltip nativo do navegador (o Streamlit não roda JS, mas honra <title>).
    escopo = f"{n} de {total} sem." if (janela and total > n) else f"{n} semanas"
    resumo = (
        f"{rotulo} - atual: {_fmt_valor(pts[-1])} · "
        f"média: {_fmt_valor(media)} · "
        f"mín–máx: {_fmt_valor(lo)}–{_fmt_valor(hi)} · {escopo}"
    )

    # Preenchimento chapado (não degradê) - url(#id)/<defs> costuma ser removido
    # pelo sanitizador de HTML do Streamlit, o que deixaria a área invisível.
    # Ordem: área → linha de média (referência) → série → ponto atual.
    return (
        f'<svg class="mv-spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
        f'<title>{resumo}</title>'
        f'<polygon points="{area}" fill="{cor}" fill-opacity="0.16"/>'
        f'<line x1="0" y1="{my:.1f}" x2="{w}" y2="{my:.1f}" stroke="#6b7280" '
        f'stroke-width="0.8" stroke-dasharray="3 3"/>'
        f'<polyline points="{linha}" fill="none" stroke="{cor}" '
        f'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.4" fill="{cor}"/>'
        f'</svg>'
    )


def _cor_de_sub(sub) -> str:
    """Escolhe a cor da linha pela tendência do subtítulo (+/-)."""
    if sub and sub.strip().startswith(("-", "−")):
        return DOWN
    return ACCENT


def _classe_tendencia(sub: str) -> str:
    """Deduz a cor do subtítulo a partir do sinal (+/-) - para deltas."""
    if not sub:
        return "flat"
    s = sub.strip()
    if s.startswith("+"):
        return "up"
    if s.startswith("-") or s.startswith("−"):
        return "down"
    return "flat"


def linha_kpis(kpis: list):
    """Renderiza uma linha de boxes de KPI estilizados (substitui st.metric cru).

    kpis: lista de dicts com chaves:
        - 'label' (str): rótulo inferior.
        - 'valor' (str): valor em destaque.
        - 'sub'   (str, opcional): subtítulo/tendência. Se começar com +/-,
          é colorido como alta/baixa automaticamente.
        - 'serie' (list, opcional): série (ex.: semanal) para a mini timeline
          (sparkline) desenhada no rodapé do box.
        - 'cor'   (str, opcional): cor do sparkline (default ACCENT).
    """
    cols = max(1, len(kpis))
    boxes = []
    for k in kpis:
        sub_html = ""
        if k.get("sub"):
            classe = _classe_tendencia(k["sub"])
            sub_html = f'<div class="sub {classe}">{k["sub"]}</div>'
        # cor explícita vence; senão segue a tendência do sub (queda = vermelho)
        cor = k.get("cor") or _cor_de_sub(k.get("sub"))
        spark_html = _sparkline_svg(k.get("serie"), cor=cor, rotulo=k.get("label", "Semanal"))
        boxes.append(
            f'<div class="mv-kpi"><div class="val">{k["valor"]}</div>'
            f'<div class="lbl">{k["label"]}</div>{sub_html}{spark_html}</div>'
        )
    st.markdown(
        f'<div class="mv-kpis" style="--mv-cols:{cols}">' + "".join(boxes) + "</div>",
        unsafe_allow_html=True,
    )
