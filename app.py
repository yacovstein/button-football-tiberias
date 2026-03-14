import streamlit as st
import json
import pandas as pd

st.set_page_config(page_title="Button Football Championship", layout="wide")

st.title("⚽ Tiberias / Migdal 2026 Button Football")

with open("state.json") as f:
    data = json.load(f)

groups = data["groups"]

results = []

st.header("Group Stage")

for g, teams in groups.items():

    st.subheader(f"Group {g}")

    cols = st.columns(3)

    matches = [
        (teams[0], teams[1]),
        (teams[2], teams[3]),
        (teams[0], teams[2]),
        (teams[1], teams[3]),
        (teams[0], teams[3]),
        (teams[1], teams[2]),
    ]

    for i,(t1,t2) in enumerate(matches):

        with cols[i%3]:

            g1 = st.number_input(f"{t1}",0,20,key=f"{g}{i}a")
            g2 = st.number_input(f"{t2}",0,20,key=f"{g}{i}b")

            if g1 or g2:

                results.append([t1,t2,g1,g2])


table = {}

for g,teams in groups.items():

    for t in teams:

        table[t] = {
            "team":t,
            "pts":0,
            "gf":0,
            "ga":0,
            "gd":0
        }

for t1,t2,g1,g2 in results:

    table[t1]["gf"] += g1
    table[t1]["ga"] += g2

    table[t2]["gf"] += g2
    table[t2]["ga"] += g1

    if g1>g2:
        table[t1]["pts"] += 3
    elif g2>g1:
        table[t2]["pts"] += 3
    else:
        table[t1]["pts"] +=1
        table[t2]["pts"] +=1

for t in table:

    table[t]["gd"] = table[t]["gf"]-table[t]["ga"]

df = pd.DataFrame(table.values())

df = df.sort_values(["pts","gd","gf"],ascending=False)

st.header("Overall Ranking")

st.dataframe(df)

top8 = df.head(8)["team"].tolist()

st.header("Knockout")

if len(top8)==8:

    st.write("Quarterfinals")

    st.write(f"{top8[0]} vs {top8[7]}")
    st.write(f"{top8[1]} vs {top8[6]}")
    st.write(f"{top8[2]} vs {top8[5]}")
    st.write(f"{top8[3]} vs {top8[4]}")

else:

    st.write("Enter group results to generate knockout stage")
