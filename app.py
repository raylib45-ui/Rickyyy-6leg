import streamlit as st
import pandas as pd
import numpy as np
import math
import requests

st.set_page_config(
    page_title="Rick C-137 Live CS2 Miner",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Rick C-137 Live CS2 PrizePicks Miner")
st.markdown("*“Live JSON board connected successfully, Morty.”*")
st.write("")

def clamp(x, low=0.01, high=0.99):
    return max(low, min(high, x))

def probability_from_z(projected, line, uncertainty):
    if uncertainty <= 0:
        uncertainty = 1
    z = (projected - line) / uncertainty
    return clamp(0.5 * (1 + math.erf(z / math.sqrt(2))))

def calculate_candidate(row):
    try:
        raw_recent = row["recent_results"]
        if isinstance(raw_recent, str):
            recent = np.array([float(x.strip()) for x in raw_recent.replace("[", "").replace("]", "").split(",")], dtype=float)
        else:
            recent = np.array(raw_recent, dtype=float)

        recent_mean = np.mean(recent)
        recent_median = np.median(recent)
        recent_std = np.std(recent, ddof=1) if len(recent) > 1 else 0.0

        projection = (
            0.25 * row["season_projection"]
            + 0.30 * recent_mean
            + 0.20 * recent_median
            + 0.15 * row["matchup_projection"]
            + 0.10 * row["role_projection"]
        ) * row["pace_volume_projection"]

        uncertainty = max(
            row["market_baseline_uncertainty"],
            recent_std * row["sport_variance_factor"]
        )

        raw_more = probability_from_z(projection, row["line"], uncertainty)
        more_prob = clamp(raw_more)
        less_prob = 1 - more_prob

        if more_prob >= less_prob:
            side = "MORE 🔨"
            model_prob = more_prob
            margin = projection - row["line"]
        else:
            side = "LESS 🔨"
            model_prob = less_prob
            margin = row["line"] - projection

        edge = model_prob - row["estimated_market_probability"]

        return {
            "player": row["player"],
            "sport": row["sport"],
            "stat": row["stat"],
            "line": row["line"],
            "side": side,
            "projection": round(projection, 2),
            "margin": round(margin, 2),
            "model_prob": round(model_prob * 100, 1),
            "edge": round(edge * 100, 2),
            "uncertainty": round(uncertainty, 3)
        }
    except Exception:
        return None

@st.cache_data(ttl=60)
def get_live_board():
    url = "https://raw.githubusercontent.com/raylib45-ui/Rickyyy-6leg/main/live_board.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception:
        pass
    return pd.DataFrame()

board_df = get_live_board()

if board_df.empty:
    st.warning("Waiting for live board data...")
else:
    candidates = []
    for _, row in board_df.iterrows():
        res = calculate_candidate(row)
        if res:
            candidates.append(res)

    if candidates:
        df_res = pd.DataFrame(candidates).sort_values(by="edge", ascending=False)
        st.success(f"Successfully processed {len(df_res)} active player props!")
        
        st.subheader("🎯 Top Player Prop Recommendations")
        for idx, row in df_res.head(6).iterrows():
            st.info(f"**{row['player']}** ({row['sport']} - {row['stat']}) | Line: **{row['line']}** | Action: **{row['side']}** | Edge: **+{row['edge']}%**")
            
        st.subheader("📊 Full Analysis Table")
        st.dataframe(df_res, use_container_width=True)

if st.button("🔄 Refresh Board Data"):
    st.cache_data.clear()
    st.rerun()
