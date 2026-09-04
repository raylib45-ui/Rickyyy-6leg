@st.cache_data(ttl=300)
def get_cs2_board():
    import requests
    url = "https://raw.githubusercontent.com/raylib45-ui/Rickyyy-6leg/main/live_board.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
    except Exception:
        pass
    return pd.DataFrame()
