import streamlit as st
import pandas as pd
import numpy as np
import math

st.set_page_config(
    page_title="Rick C-137 24/7 Live Player Props Miner",
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00ff66; }
    .stButton>button { background-color: #00ff66; color: #0e1117; font-weight: bold; border-radius: 4px; }
    .hammer-card {
        background-color: #161b22;
        border: 2px solid #00ff66;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .live-badge {
        background-color: #00ff66;
        color: #0e1117;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

MIN_EDGE = -999.0
MIN_PROB = 0.0
MAX_UNCERTAINTY = 999.0
MIN_SAMPLE = 1

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

        if len(recent) < MIN_SAMPLE:
            return None

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
        raw_less = 1 - raw_more

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

st.title("🧪 Rick C-137 24/7 Live Player Props Miner")
st.markdown("*“Hardcoded fallback data was holding onto old board entries, Morty. Use the live CSV uploader below to feed current PrizePicks lines instantly.”*")
st.markdown('<span class="live-badge">🟢 LIVE 24/7 PLAYER PROPS ACTIVE</span>', unsafe_allow_html=True)
st.write("")

# Blank default DataFrame so old expired players don't show unless loaded via CSV or updated live board
@st.cache_data(ttl=600)
def get_live_player_props_board():
    return pd.DataFrame(columns=[
        "player", "sport", "stat", "line", "recent_results", 
        "season_projection", "matchup_projection", "role_projection", 
        "pace_volume_projection", "market_baseline_uncertainty", 
        "sport_variance_factor", "estimated_market_probability"
    ])

uploaded_file = st.file_uploader("Upload Current PrizePicks Board CSV", type=["csv"])

if uploaded_file is not None:
    board_df = pd.read_csv(uploaded_file)
    st.success("Successfully loaded custom board CSV!")
else:
    st.info("💡 **Action Required:** Upload your current PrizePicks CSV export below or paste your live lines. (The old cached fallback players have been cleared so nothing expired shows up).")
    board_df = get_live_player_props_board()

if board_df.empty:
    st.warning("No active player props loaded. Please upload a CSV file containing your active board lines to generate the model slip.")
else:
    candidates = []
    for _, row in board_df.iterrows():
        res = calculate_candidate(row)
        if res:
            candidates.append(res)

    if not candidates:
        st.error("No valid player prop rows found. Check CSV structure.")
    else:
        df_res = pd.DataFrame(candidates).sort_values(by="edge", ascending=False)
        st.success(f"Successfully processed {len(df_res)} active individual player props!")
        
        st.subheader("🎯 Live Top 6-Leg Player Prop Slip")
        parlay_picks = df_res.head(6)
        
        for idx, row in parlay_picks.iterrows():
            st.markdown(f"""
            <div class="hammer-card">
                <b>{row['player']}</b> ({row['sport']} - {row['stat']})<br>
                Line: <b>{row['line']}</b> | Action: <span style="color:#00ff66;"><b>{row['side']}</b></span><br>
                Model Prob: <b>{row['model_prob']}%</b> | Edge: <b>+{row['edge']}%</b> | Projection: <b>{row['projection']}</b>
            </div>
            """, unsafe_allow_html=True)
            
        st.subheader("📊 Full Active Player Props Analysis Table")
        st.dataframe(df_res, use_container_width=True)

if st.button("🔄 Clear Cache & Refresh"):
    st.cache_data.clear()
    st.rerun()
