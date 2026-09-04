import requests
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300) # Refreshes automatically every 5 minutes
def fetch_live_prizepicks_board():
    # Replace this URL with your hosted JSON endpoint or raw GitHub JSON file path
    live_json_url = "https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO/main/live_board.json"
    
    try:
        response = requests.get(live_json_url)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Could not reach live JSON feed: {e}")
        
    # Empty fallback dataframe if offline
    return pd.DataFrame(columns=[
        "player", "sport", "stat", "line", "recent_results", 
        "season_projection", "matchup_projection", "role_projection", 
        "pace_volume_projection", "market_baseline_uncertainty", 
        "sport_variance_factor", "estimated_market_probability"
    ])

board_df = fetch_live_prizepicks_board()
