
import streamlit as st
import pandas as pd
import requests
from datetime import date
from io import BytesIO

# Constants
API_KEY = st.secrets["sportsdata_api_key"]
BASE_URL = "https://api.sportsdata.io/v3/nba/stats/json"
HEADERS = {"Ocp-Apim-Subscription-Key": API_KEY}

def get_today_games():
    today = date.today().isoformat()
    url = f"{BASE_URL}/GamesByDate/{today}"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def get_player_stats(game_id):
    url = f"{BASE_URL}/PlayerGameStatsByGame/{game_id}"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def run_predictive_formula(player_stats):
    # Placeholder: implement your actual NBA predictive formula here
    predictions = []
    for player in player_stats:
        if player['Minutes'] > 0:
            pred_pts = round(player['Points'] * 1.05, 1)
            pred_reb = round(player['Rebounds'] * 1.05, 1)
            pred_ast = round(player['Assists'] * 1.05, 1)
            predictions.append({
                "Name": player['Name'],
                "Team": player['Team'],
                "Opponent": player['Opponent'],
                "Predicted PTS": pred_pts,
                "Predicted REB": pred_reb,
                "Predicted AST": pred_ast
            })
    return pd.DataFrame(predictions)

def create_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Predictions')
        writer.save()
    output.seek(0)
    return output

# Streamlit App
st.title("NBA Predictive Formula Tool")
st.subheader("Today's Game Predictions")

with st.spinner('Loading today\'s games...'):
    games = get_today_games()

game_options = {f"{g['AwayTeam']} @ {g['HomeTeam']} ({g['DateTime'][:10]})": g['GameID'] for g in games}
selected_game = st.selectbox("Select a game:", list(game_options.keys()))

game_id = game_options[selected_game]

with st.spinner('Fetching player stats...'):
    player_stats = get_player_stats(game_id)

if player_stats:
    df_predictions = run_predictive_formula(player_stats)
    st.dataframe(df_predictions)

    excel_data = create_excel_download(df_predictions)
    st.download_button(
        label="📥 Download Predictions as Excel",
        data=excel_data,
        file_name="nba_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("No player stats available for this game.")
