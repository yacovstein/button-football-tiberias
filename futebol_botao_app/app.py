
import json, base64
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tiberias / Migdal 2026 Button Football Championship", page_icon="🏆", layout="wide")
APP_DIR = Path(__file__).parent
STATE_FILE = APP_DIR / "state.json"
ASSETS_DIR = APP_DIR / "assets_real"
COVER_FILE = APP_DIR / "cover.png"

TEAM_META = {
    "Arsenal": {"coach":"Daniel","colors":["#EF0107","#FFFFFF"]},
    "Barcelona": {"coach":"Daniel","colors":["#A50044","#004D98"]},
    "Bayern Munique": {"coach":"Yehoshua","colors":["#DC052D","#0066B2"]},
    "Boca Juniors": {"coach":"Yehoshua","colors":["#0033A0","#F7D117"]},
    "Corinthians": {"coach":"Daniel","colors":["#111111","#FFFFFF"]},
    "Flamengo": {"coach":"Calebe","colors":["#C8102E","#111111"]},
    "Guarani": {"coach":"Yehoshua","colors":["#006B3F","#FFFFFF"]},
    "Internazionale": {"coach":"David","colors":["#00529F","#111111"]},
    "Juventus": {"coach":"Daniel","colors":["#111111","#FFFFFF"]},
    "Liverpool": {"coach":"Calebe","colors":["#C8102E","#00B2A9"]},
    "Manchester United": {"coach":"Daniel","colors":["#DA291C","#FBE122"]},
    "Manchester City": {"coach":"Calebe","colors":["#6CABDD","#1C2C5B"]},
    "Milan": {"coach":"David","colors":["#C00000","#111111"]},
    "Palmeiras": {"coach":"David","colors":["#006437","#FFFFFF"]},
    "Portuguesa": {"coach":"David","colors":["#C8102E","#0B7A3B"]},
    "Real Madrid": {"coach":"David","colors":["#FEBE10","#FFFFFF"]},
    "River Plate": {"coach":"Calebe","colors":["#FFFFFF","#D71920"]},
    "Santos": {"coach":"Calebe","colors":["#111111","#FFFFFF"]},
    "São Paulo": {"coach":"Yehoshua","colors":["#111111","#D71920"]},
    "Vasco": {"coach":"Yehoshua","colors":["#111111","#FFFFFF"]},
}


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else load_seed()

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def img_to_data_uri(path: Path):
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("utf-8")

def team_badge_html(team: str, size=38):
    uri = img_to_data_uri(ASSETS_DIR / f"{team}.png")
    coach = TEAM_META[team]["coach"]
    return f"""
    <div style="display:flex;align-items:center;gap:10px;">
      <img src="{uri}" width="{size}" height="{size}" style="object-fit:contain;background:rgba(255,255,255,.04);border-radius:10px;padding:2px;" />
      <div>
        <div style="font-weight:700;line-height:1.1;">{team}</div>
        <div style="font-size:12px;opacity:.78;line-height:1.1;">Coach: {coach}</div>
      </div>
    </div>
    """

def compute_group_tables(state):
    tables = {}
    for group, teams in state["groups"].items():
        stats = {team: {"Equipe":team,"Grupo":group,"Coach":TEAM_META[team]["coach"],"Pts":0,"V":0,"E":0,"D":0,"GP":0,"GC":0,"SG":0,"J":0} for team in teams}
        for match in state["fixtures"]:
            if match["group"] != group or match["home_goals"] is None or match["away_goals"] is None:
                continue
            hg, ag = match["home_goals"], match["away_goals"]
            h, a = match["home"], match["away"]
            stats[h]["J"] += 1; stats[a]["J"] += 1
            stats[h]["GP"] += hg; stats[h]["GC"] += ag
            stats[a]["GP"] += ag; stats[a]["GC"] += hg
            if hg > ag:
                stats[h]["Pts"] += 3; stats[h]["V"] += 1; stats[a]["D"] += 1
            elif ag > hg:
                stats[a]["Pts"] += 3; stats[a]["V"] += 1; stats[h]["D"] += 1
            else:
                stats[h]["Pts"] += 1; stats[a]["Pts"] += 1; stats[h]["E"] += 1; stats[a]["E"] += 1
        for team in teams:
            stats[team]["SG"] = stats[team]["GP"] - stats[team]["GC"]
        table = pd.DataFrame(stats.values()).sort_values(by=["Pts","V","SG","GP","Equipe"], ascending=[False,False,False,False,True], ignore_index=True)
        table.insert(0, "Pos", range(1, len(table)+1))
        tables[group] = table
    return tables

def overall_qualified(group_tables):
    rows = []
    for _, table in group_tables.items():
        rows.extend(table.to_dict("records"))
    overall = pd.DataFrame(rows).sort_values(by=["Pts","V","SG","GP","Equipe"], ascending=[False,False,False,False,True], ignore_index=True)
    overall.insert(0, "Seed", range(1, len(overall)+1))
    return overall.head(8).copy(), overall

def get_knockout_structure(qualified, state):
    seed_map = {row["Seed"]: row["Equipe"] for row in qualified[["Seed","Equipe"]].to_dict("records")}
    ko = state.get("knockout", {})
    quarter_pairs = [("QF1",1,8),("QF2",2,7),("QF3",3,6),("QF4",4,5)]
    quarterfinals = []
    for code, s1, s2 in quarter_pairs:
        m = ko.get(code, {})
        t1, t2 = seed_map.get(s1, f"{s1}º"), seed_map.get(s2, f"{s2}º")
        g1, g2 = m.get("g1"), m.get("g2")
        winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
        quarterfinals.append({"code":code,"time1":t1,"g1":g1,"g2":g2,"time2":t2,"winner":winner})
    semifinals = []
    for code, a, b in [("SF1","QF1","QF2"),("SF2","QF3","QF4")]:
        m = ko.get(code, {})
        t1 = next((x["winner"] for x in quarterfinals if x["code"] == a), f"Winner {a}")
        t2 = next((x["winner"] for x in quarterfinals if x["code"] == b), f"Winner {b}")
        g1, g2 = m.get("g1"), m.get("g2")
        winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
        semifinals.append({"code":code,"time1":t1,"g1":g1,"g2":g2,"time2":t2,"winner":winner})
    m = ko.get("FINAL", {})
    t1 = semifinals[0]["winner"] if semifinals[0]["winner"] else "Winner SF1"
    t2 = semifinals[1]["winner"] if semifinals[1]["winner"] else "Winner SF2"
    g1, g2 = m.get("g1"), m.get("g2")
    winner = t1 if g1 is not None and g2 is not None and g1 > g2 else t2 if g1 is not None and g2 is not None and g2 > g1 else None
    return quarterfinals, semifinals, {"code":"FINAL","time1":t1,"g1":g1,"g2":g2,"time2":t2,"winner":winner}

def render_cover():
    uri = img_to_data_uri(COVER_FILE)
    st.markdown(f'<div style="margin-bottom:18px;"><img src="{uri}" style="width:100%;max-width:840px;display:block;margin:0 auto;border-radius:22px;box-shadow:0 18px 42px rgba(0,0,0,.28);" /></div>', unsafe_allow_html=True)

def render_group_table(df, title):
    rows_html = ""
    for _, row in df.iterrows():
        team = row["Equipe"]
        highlight = "background:rgba(255,255,255,.045);" if row["Pos"] <= 2 else ""
        rows_html += f'<tr style="{highlight}"><td style="padding:10px 8px;">{int(row["Pos"])}</td><td style="padding:10px 8px;">{team_badge_html(team, 34)}</td><td style="padding:10px 8px;">{row["Coach"]}</td><td style="padding:10px 8px;text-align:center;">{int(row["Pts"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["J"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["V"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["E"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["D"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["GP"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["GC"])}</td><td style="padding:10px 8px;text-align:center;">{int(row["SG"])}</td></tr>'
    st.markdown(f"#### {title}")
    st.markdown(f'<div class="glass"><table style="width:100%;border-collapse:collapse;"><thead><tr><th>Pos</th><th>Team</th><th>Coach</th><th>Pts</th><th>J</th><th>V</th><th>E</th><th>D</th><th>GP</th><th>GC</th><th>SG</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)

def fixture_row(match, idx, state):
    c1, c2, c3, c4, c5 = st.columns([4.2, 1, 0.6, 1, 4.2])
    with c1: st.markdown(team_badge_html(match["home"], 38), unsafe_allow_html=True)
    with c2: g1 = st.number_input(f'g1_{idx}', min_value=0, step=1, value=match["home_goals"] if match["home_goals"] is not None else 0)
    with c3: st.markdown("<div style='text-align:center;font-size:26px;padding-top:10px;'>x</div>", unsafe_allow_html=True)
    with c4: g2 = st.number_input(f'g2_{idx}', min_value=0, step=1, value=match["away_goals"] if match["away_goals"] is not None else 0)
    with c5: st.markdown(team_badge_html(match["away"], 38), unsafe_allow_html=True)
    if st.button(f"Save match {idx+1}", key=f"save_group_{idx}", use_container_width=True):
        state["fixtures"][idx]["home_goals"] = int(g1); state["fixtures"][idx]["away_goals"] = int(g2); save_state(state); st.success("Match saved."); st.rerun()

def render_seed_cards(overall):
    st.markdown("### Top 8, qualified for knockout stage")
    cols = st.columns(4)
    for i, (_, row) in enumerate(overall.head(8).iterrows()):
        team = row["Equipe"]; colors = TEAM_META[team]["colors"]
        with cols[i % 4]:
            st.markdown(f'''<div style="background:linear-gradient(135deg,{colors[0]} 0%, #0d1320 100%);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:14px;box-shadow:0 10px 24px rgba(0,0,0,.24);margin-bottom:12px;"><div style="font-size:12px;opacity:.88;">Seed #{int(row["Seed"])}</div>{team_badge_html(team, 48)}<div style="display:flex;gap:14px;margin-top:12px;font-size:13px;"><div><b>{int(row["Pts"])}</b><br/>Pts</div><div><b>{int(row["V"])}</b><br/>W</div><div><b>{int(row["SG"])}</b><br/>GD</div><div><b>{int(row["GP"])}</b><br/>GF</div></div></div>''', unsafe_allow_html=True)

def knockout_card(match, state):
    t1, t2 = match["time1"], match["time2"]
    c1, c2, c3 = st.columns([2.7, 2.2, 2.7])
    with c1: st.markdown(team_badge_html(t1, 40), unsafe_allow_html=True) if t1 in TEAM_META else st.write(t1)
    with c2:
        a, b, c = st.columns([1,0.5,1])
        g1 = a.number_input(f'{match["code"]}_g1', min_value=0, step=1, value=match["g1"] if match["g1"] is not None else 0, key=f'{match["code"]}_g1')
        b.markdown("<div style='text-align:center;font-size:24px;padding-top:6px;'>x</div>", unsafe_allow_html=True)
        g2 = c.number_input(f'{match["code"]}_g2', min_value=0, step=1, value=match["g2"] if match["g2"] is not None else 0, key=f'{match["code"]}_g2')
        if st.button(f"Save {match['code']}", key=f"save_{match['code']}", use_container_width=True):
            state.setdefault("knockout", {})[match["code"]] = {"g1": int(g1), "g2": int(g2)}; save_state(state); st.success(f"{match['code']} saved."); st.rerun()
        if match["winner"]: st.success(f"Qualified: {match['winner']}")
    with c3: st.markdown(team_badge_html(t2, 40), unsafe_allow_html=True) if t2 in TEAM_META else st.write(t2)

state = load_state()

st.markdown("""
<style>
.stApp {background:radial-gradient(circle at top left, rgba(255,215,0,.12), transparent 22%), linear-gradient(180deg, #08121c 0%, #0d1827 100%); color:#f4f7fb;}
.glass {background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); border-radius: 18px; padding: 14px; backdrop-filter: blur(10px); box-shadow: 0 10px 30px rgba(0,0,0,.18); margin-bottom: 16px;}
table th {text-align:left; padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.12); color:#f0d37b;}
table td {border-bottom:1px solid rgba(255,255,255,.06); vertical-align:middle;}
</style>
""", unsafe_allow_html=True)

render_cover()
top1, top2, top3 = st.columns([1,1,1])
with top1:
    if st.button("Restore initial state", use_container_width=True):
        if STATE_FILE.exists(): STATE_FILE.unlink()
        st.success("Initial state restored."); st.rerun()
with top2:
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    st.download_button("Download results (JSON)", payload.encode("utf-8"), "tiberias_migdal_2026_results.json", "application/json", use_container_width=True)
with top3:
    total_games = len(state["fixtures"]); done_games = sum(1 for m in state["fixtures"] if m["home_goals"] is not None and m["away_goals"] is not None)
    st.markdown(f"<div class='glass' style='text-align:center;padding:12px;'><div style='font-size:13px;opacity:.8;'>Matches filled</div><div style='font-size:26px;font-weight:800;'>{done_games} / {total_games}</div></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Group Stage", "Standings", "Knockout", "Coaches"])
with tab1:
    st.subheader("Group stage results")
    for group in ["A","B","C","D","E"]:
        st.markdown(f"### Group {group}")
        for idx, match in enumerate(state["fixtures"]):
            if match["group"] != group: continue
            st.markdown(f"<div class='glass'><div style='font-size:13px;opacity:.75;margin-bottom:8px;'>{match['round']}</div>", unsafe_allow_html=True)
            fixture_row(match, idx, state)
            st.markdown("</div>", unsafe_allow_html=True)
with tab2:
    tables = compute_group_tables(state); qualified, overall = overall_qualified(tables)
    render_seed_cards(qualified)
    for group in ["A","B","C","D","E"]: render_group_table(tables[group], f"Group {group}")
    render_group_table(overall, "Overall ranking")
with tab3:
    tables = compute_group_tables(state); qualified, _ = overall_qualified(tables)
    qf, sf, final = get_knockout_structure(qualified, state)
    st.markdown("### Quarterfinals")
    for m in qf: st.markdown("<div class='glass'>", unsafe_allow_html=True); knockout_card(m, state); st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("### Semifinals")
    for m in sf: st.markdown("<div class='glass'>", unsafe_allow_html=True); knockout_card(m, state); st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("### Final"); st.markdown("<div class='glass'>", unsafe_allow_html=True); knockout_card(final, state); st.markdown("</div>", unsafe_allow_html=True)
    if final["winner"]:
        champ = final["winner"]; uri = img_to_data_uri(ASSETS_DIR / f"{champ}.png")
        st.markdown(f'<div class="glass" style="text-align:center;background:linear-gradient(135deg,#caa24e, #0d1320);padding:20px;"><div style="font-size:13px;letter-spacing:1px;opacity:.9;">CHAMPION</div><img src="{uri}" width="110" style="object-fit:contain;margin:8px auto 10px auto;display:block;" /><div style="font-size:32px;font-weight:900;">{champ}</div><div style="margin-top:6px;">Coach: {TEAM_META[champ]["coach"]}</div></div>', unsafe_allow_html=True)
with tab4:
    st.subheader("Teams by coach")
    coaches = {}
    for team, meta in TEAM_META.items(): coaches.setdefault(meta["coach"], []).append(team)
    cols = st.columns(2)
    for i, (coach, teams) in enumerate(sorted(coaches.items())):
        with cols[i % 2]:
            cards = "".join([f"<li style='list-style:none;margin-bottom:8px;'>{team_badge_html(t, 30)}</li>" for t in sorted(teams)])
            st.markdown(f"<div class='glass'><div style='font-size:24px;font-weight:800;'>{coach}</div><ul style='padding-left:0;margin-top:12px;'>{cards}</ul></div>", unsafe_allow_html=True)
