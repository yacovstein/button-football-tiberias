import base64
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tiberias / Migdal 2026 Button Football Championship", page_icon="🏆", layout="wide")

APP_DIR = Path(__file__).parent
ASSETS_DIR = APP_DIR / "assets"
COVER_FILE = APP_DIR / "cover.png"
STATE_FILE = APP_DIR / "state.json"
INITIAL_STATE_FILE = APP_DIR / "initial_state.json"

TEAM_META = {
    "Arsenal": {"coach": "Daniel", "colors": ["#EF0107", "#FFFFFF"]},
    "Barcelona": {"coach": "Daniel", "colors": ["#A50044", "#004D98"]},
    "Bayern Munique": {"coach": "Yehoshua", "colors": ["#DC052D", "#0066B2"]},
    "Boca Juniors": {"coach": "Yehoshua", "colors": ["#0033A0", "#F7D117"]},
    "Corinthians": {"coach": "Daniel", "colors": ["#111111", "#FFFFFF"]},
    "Flamengo": {"coach": "Calebe", "colors": ["#C8102E", "#111111"]},
    "Guarani": {"coach": "Yehoshua", "colors": ["#006B3F", "#FFFFFF"]},
    "Internazionale": {"coach": "David", "colors": ["#00529F", "#111111"]},
    "Juventus": {"coach": "Daniel", "colors": ["#111111", "#FFFFFF"]},
    "Liverpool": {"coach": "Calebe", "colors": ["#C8102E", "#00B2A9"]},
    "Manchester United": {"coach": "Daniel", "colors": ["#DA291C", "#FBE122"]},
    "Manchester City": {"coach": "Calebe", "colors": ["#6CABDD", "#1C2C5B"]},
    "Milan": {"coach": "David", "colors": ["#C00000", "#111111"]},
    "Palmeiras": {"coach": "David", "colors": ["#006437", "#FFFFFF"]},
    "Portuguesa": {"coach": "David", "colors": ["#C8102E", "#0B7A3B"]},
    "Real Madrid": {"coach": "David", "colors": ["#FEBE10", "#FFFFFF"]},
    "River Plate": {"coach": "Calebe", "colors": ["#FFFFFF", "#D71920"]},
    "Santos": {"coach": "Calebe", "colors": ["#111111", "#FFFFFF"]},
    "São Paulo": {"coach": "Yehoshua", "colors": ["#111111", "#D71920"]},
    "Vasco": {"coach": "Yehoshua", "colors": ["#111111", "#FFFFFF"]},
}

ALIASES = {
    "Bayern": "Bayern Munique",
    "Sao Paulo": "São Paulo",
}


def canonical_team(name: str) -> str:
    base = str(name).split(" (")[0].strip()
    return ALIASES.get(base, base)


def load_initial_state() -> dict:
    return json.loads(INITIAL_STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict:
    if not STATE_FILE.exists():
        state = deepcopy(load_initial_state())
        save_state(state)
        return state
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError
        if "groups" not in state or "fixtures" not in state or "knockout" not in state:
            raise ValueError
        return state
    except Exception:
        state = deepcopy(load_initial_state())
        save_state(state)
        return state


def img_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("utf-8")


def team_badge_html(display_name: str, size: int = 40) -> str:
    team_key = canonical_team(display_name)
    uri = img_to_data_uri(ASSETS_DIR / f"{team_key}.png")
    coach = TEAM_META.get(team_key, {}).get("coach", "Unknown")

    return f"""<div style="display:flex;align-items:center;gap:10px;">
<img src="{uri}" width="{size}" height="{size}" style="object-fit:contain;background:rgba(255,255,255,.04);border-radius:10px;padding:2px;" />
<div>
<div style="font-weight:700;line-height:1.1;">{display_name}</div>
<div style="font-size:12px;opacity:.78;line-height:1.1;">Coach: {coach}</div>
</div>
</div>"""


def compute_group_tables(state: dict) -> dict:
    tables = {}
    for group, teams in state["groups"].items():
        stats = {}
        for team in teams:
            key = canonical_team(team)
            stats[team] = {
                "Equipe": team,
                "Grupo": group,
                "Coach": TEAM_META.get(key, {}).get("coach", "Unknown"),
                "Pts": 0,
                "V": 0,
                "E": 0,
                "D": 0,
                "GP": 0,
                "GC": 0,
                "SG": 0,
                "J": 0,
            }
        for match in state["fixtures"]:
            if match["group"] != group:
                continue
            hg, ag = match.get("home_goals"), match.get("away_goals")
            if hg is None or ag is None:
                continue
            home, away = match["home"], match["away"]
            if home not in stats or away not in stats:
                continue
            stats[home]["J"] += 1
            stats[away]["J"] += 1
            stats[home]["GP"] += hg
            stats[home]["GC"] += ag
            stats[away]["GP"] += ag
            stats[away]["GC"] += hg
            if hg > ag:
                stats[home]["Pts"] += 3
                stats[home]["V"] += 1
                stats[away]["D"] += 1
            elif ag > hg:
                stats[away]["Pts"] += 3
                stats[away]["V"] += 1
                stats[home]["D"] += 1
            else:
                stats[home]["Pts"] += 1
                stats[away]["Pts"] += 1
                stats[home]["E"] += 1
                stats[away]["E"] += 1
        for team in teams:
            stats[team]["SG"] = stats[team]["GP"] - stats[team]["GC"]
        table = pd.DataFrame(stats.values()).sort_values(
            by=["Pts", "V", "SG", "GP", "Equipe"],
            ascending=[False, False, False, False, True],
            ignore_index=True,
        )
        table.insert(0, "Pos", range(1, len(table) + 1))
        tables[group] = table
    return tables


def overall_qualified(group_tables: dict):
    rows = []
    for table in group_tables.values():
        rows.extend(table.to_dict("records"))
    overall = pd.DataFrame(rows).sort_values(
        by=["Pts", "V", "SG", "GP", "Equipe"],
        ascending=[False, False, False, False, True],
        ignore_index=True,
    )
    overall.insert(0, "Seed", range(1, len(overall) + 1))
    return overall.head(8).copy(), overall


def get_knockout_structure(qualified: pd.DataFrame, state: dict):
    seed_map = {int(row["Seed"]): row["Equipe"] for _, row in qualified.iterrows()}
    ko = state.get("knockout", {})
    qf = []
    for code, a, b in [("QF1", 1, 8), ("QF2", 2, 7), ("QF3", 3, 6), ("QF4", 4, 5)]:
        item = ko.get(code, {})
        t1, t2 = seed_map.get(a, f"{a}º"), seed_map.get(b, f"{b}º")
        g1, g2 = item.get("g1"), item.get("g2")
        winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
        qf.append({"code": code, "time1": t1, "time2": t2, "g1": g1, "g2": g2, "winner": winner})
    sf = []
    for code, a, b in [("SF1", "QF1", "QF2"), ("SF2", "QF3", "QF4")]:
        item = ko.get(code, {})
        t1 = next((m["winner"] for m in qf if m["code"] == a), f"Winner {a}")
        t2 = next((m["winner"] for m in qf if m["code"] == b), f"Winner {b}")
        g1, g2 = item.get("g1"), item.get("g2")
        winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
        sf.append({"code": code, "time1": t1, "time2": t2, "g1": g1, "g2": g2, "winner": winner})
    item = ko.get("FINAL", {})
    t1 = sf[0]["winner"] if sf and sf[0]["winner"] else "Winner SF1"
    t2 = sf[1]["winner"] if len(sf) > 1 and sf[1]["winner"] else "Winner SF2"
    g1, g2 = item.get("g1"), item.get("g2")
    winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
    return qf, sf, {"code": "FINAL", "time1": t1, "time2": t2, "g1": g1, "g2": g2, "winner": winner}


def render_cover() -> None:
    uri = img_to_data_uri(COVER_FILE)
    st.markdown(
        f'<div style="margin-bottom:18px;"><img src="{uri}" style="width:100%;max-width:840px;display:block;margin:0 auto;border-radius:22px;box-shadow:0 18px 42px rgba(0,0,0,.28);" /></div>',
        unsafe_allow_html=True,
    )


def fixture_row(match: dict, idx: int, state: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns([4.2, 1, 0.6, 1, 4.2])
    with c1:
        st.markdown(team_badge_html(match["home"], 38), unsafe_allow_html=True)
    with c2:
        g1 = st.number_input(f'g1_{idx}', min_value=0, step=1, value=match["home_goals"] if match["home_goals"] is not None else 0)
    with c3:
        st.markdown("<div style='text-align:center;font-size:26px;padding-top:10px;'>x</div>", unsafe_allow_html=True)
    with c4:
        g2 = st.number_input(f'g2_{idx}', min_value=0, step=1, value=match["away_goals"] if match["away_goals"] is not None else 0)
    with c5:
        st.markdown(team_badge_html(match["away"], 38), unsafe_allow_html=True)
    if st.button(f"Save match {idx + 1}", key=f"save_group_{idx}", use_container_width=True):
        state["fixtures"][idx]["home_goals"] = int(g1)
        state["fixtures"][idx]["away_goals"] = int(g2)
        save_state(state)
        st.success("Match saved.")
        st.rerun()


def render_group_table(df: pd.DataFrame, title: str) -> None:
    rows_html = []
    for _, row in df.iterrows():
        team = row["Equipe"]
        highlight = "background:rgba(255,255,255,.045);" if int(row["Pos"]) <= 2 else ""
        row_html = f"""<tr style="{highlight}">
<td style="padding:10px 8px;">{int(row['Pos'])}</td>
<td style="padding:10px 8px;">{team_badge_html(team, 34)}</td>
<td style="padding:10px 8px;">{row['Coach']}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['Pts'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['J'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['V'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['E'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['D'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['GP'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['GC'])}</td>
<td style="padding:10px 8px;text-align:center;">{int(row['SG'])}</td>
</tr>"""
        rows_html.append(row_html)
    st.markdown(f"#### {title}")
    st.markdown(
        f'<div class="glass"><table style="width:100%;border-collapse:collapse;"><thead><tr><th>Pos</th><th>Team</th><th>Coach</th><th>Pts</th><th>J</th><th>V</th><th>E</th><th>D</th><th>GP</th><th>GC</th><th>SG</th></tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_seed_cards(overall: pd.DataFrame) -> None:
    st.markdown("### Top 8, qualified for knockout stage")
    cols = st.columns(4)

    for i, (_, row) in enumerate(overall.head(8).iterrows()):
        team = row["Equipe"]
        key = canonical_team(team)
        colors = TEAM_META.get(key, {}).get("colors", ["#444444", "#FFFFFF"])

        card_html = f"""<div style="
background: linear-gradient(135deg, {colors[0]} 0%, #0d1320 100%);
border: 1px solid rgba(255,255,255,.10);
border-radius: 18px;
padding: 14px;
box-shadow: 0 10px 24px rgba(0,0,0,.24);
margin-bottom: 12px;
">
<div style="font-size:12px;opacity:.88;">Seed #{int(row["Seed"])}</div>
{team_badge_html(team, 48)}
<div style="display:flex;gap:14px;margin-top:12px;font-size:13px;">
<div><b>{int(row["Pts"])}</b><br/>Pts</div>
<div><b>{int(row["V"])}</b><br/>W</div>
<div><b>{int(row["SG"])}</b><br/>GD</div>
<div><b>{int(row["GP"])}</b><br/>GF</div>
</div>
</div>"""

        with cols[i % 4]:
            st.markdown(card_html, unsafe_allow_html=True)


def knockout_card(match: dict, state: dict) -> None:
    t1, t2 = match["time1"], match["time2"]
    c1, c2, c3 = st.columns([2.7, 2.2, 2.7])
    with c1:
        st.markdown(team_badge_html(t1, 40), unsafe_allow_html=True) if "Winner" not in str(t1) and "º" not in str(t1) else st.write(t1)
    with c2:
        a, b, c = st.columns([1, 0.5, 1])
        g1 = a.number_input(f'{match["code"]}_g1', min_value=0, step=1, value=match["g1"] if match["g1"] is not None else 0, key=f'{match["code"]}_g1')
        b.markdown("<div style='text-align:center;font-size:24px;padding-top:6px;'>x</div>", unsafe_allow_html=True)
        g2 = c.number_input(f'{match["code"]}_g2', min_value=0, step=1, value=match["g2"] if match["g2"] is not None else 0, key=f'{match["code"]}_g2')
        if st.button(f"Save {match['code']}", key=f"save_{match['code']}", use_container_width=True):
            state.setdefault("knockout", {})[match["code"]] = {"g1": int(g1), "g2": int(g2)}
            save_state(state)
            st.success(f"{match['code']} saved.")
            st.rerun()
        if match["winner"]:
            st.success(f"Qualified: {match['winner']}")
    with c3:
        st.markdown(team_badge_html(t2, 40), unsafe_allow_html=True) if "Winner" not in str(t2) and "º" not in str(t2) else st.write(t2)


state = load_state()

st.markdown(
    """
<style>
.stApp {
    background: radial-gradient(circle at top left, rgba(255,215,0,.12), transparent 22%), linear-gradient(180deg, #08121c 0%, #0d1827 100%);
    color:#f4f7fb;
}
.glass {
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 18px;
    padding: 14px;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px rgba(0,0,0,.18);
    margin-bottom: 16px;
}
table th {
    text-align:left;
    padding:10px 8px;
    border-bottom:1px solid rgba(255,255,255,.12);
    color:#f0d37b;
}
table td {
    border-bottom:1px solid rgba(255,255,255,.06);
    vertical-align:middle;
}
</style>
""",
    unsafe_allow_html=True,
)

render_cover()

top1, top2, top3 = st.columns([1, 1, 1])
with top1:
    if st.button("Restore initial state", use_container_width=True):
        state = deepcopy(load_initial_state())
        save_state(state)
        st.success("Initial state restored.")
        st.rerun()
with top2:
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    st.download_button("Download results (JSON)", payload.encode("utf-8"), "tiberias_migdal_2026_results.json", "application/json", use_container_width=True)
with top3:
    total_games = len(state["fixtures"])
    done_games = sum(1 for m in state["fixtures"] if m["home_goals"] is not None and m["away_goals"] is not None)
    st.markdown(f"<div class='glass' style='text-align:center;padding:12px;'><div style='font-size:13px;opacity:.8;'>Matches filled</div><div style='font-size:26px;font-weight:800;'>{done_games} / {total_games}</div></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Group Stage", "Standings", "Knockout", "Coaches"])

with tab1:
    st.subheader("Group stage results")
    for group in ["A", "B", "C", "D", "E"]:
        st.markdown(f"### Group {group}")
        for idx, match in enumerate(state["fixtures"]):
            if match["group"] != group:
                continue
            st.markdown(f"<div class='glass'><div style='font-size:13px;opacity:.75;margin-bottom:8px;'>{match['round']}</div>", unsafe_allow_html=True)
            fixture_row(match, idx, state)
            st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    tables = compute_group_tables(state)
    qualified, overall = overall_qualified(tables)
    render_seed_cards(qualified)
    for group in ["A", "B", "C", "D", "E"]:
        render_group_table(tables[group], f"Group {group}")
    render_group_table(overall, "Overall ranking")

with tab3:
    tables = compute_group_tables(state)
    qualified, _ = overall_qualified(tables)
    qf, sf, final = get_knockout_structure(qualified, state)
    st.markdown("### Quarterfinals")
    for match in qf:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        knockout_card(match, state)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("### Semifinals")
    for match in sf:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        knockout_card(match, state)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("### Final")
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    knockout_card(final, state)
    st.markdown("</div>", unsafe_allow_html=True)
    if final["winner"]:
        champ = final["winner"]
        key = canonical_team(champ)
        uri = img_to_data_uri(ASSETS_DIR / f"{key}.png")
        coach = TEAM_META.get(key, {}).get("coach", "Unknown")
        st.markdown(f'<div class="glass" style="text-align:center;background:linear-gradient(135deg,#caa24e, #0d1320);padding:20px;"><div style="font-size:13px;letter-spacing:1px;opacity:.9;">CHAMPION</div><img src="{uri}" width="110" style="object-fit:contain;margin:8px auto 10px auto;display:block;" /><div style="font-size:32px;font-weight:900;">{champ}</div><div style="margin-top:6px;">Coach: {coach}</div></div>', unsafe_allow_html=True)

with tab4:
    st.subheader("Teams by coach")
    coaches = {}
    for team, meta in TEAM_META.items():
        coaches.setdefault(meta["coach"], []).append(team)
    cols = st.columns(2)
    for i, (coach, teams) in enumerate(sorted(coaches.items())):
        with cols[i % 2]:
            cards = "".join([f"<li style='list-style:none;margin-bottom:8px;'>{team_badge_html(t, 30)}</li>" for t in sorted(teams)])
            st.markdown(f"<div class='glass'><div style='font-size:24px;font-weight:800;'>{coach}</div><ul style='padding-left:0;margin-top:12px;'>{cards}</ul></div>", unsafe_allow_html=True)
