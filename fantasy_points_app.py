import psycopg2
from sqlalchemy import create_engine
import datetime
import pandas as pd
import numpy as np
import os
import streamlit as st
st.set_page_config(layout="wide")

@st.cache_data
def load_data(sql_param):
    df = conn.query('select * from boxscore left join players on boxscore."PLAYER_ID" = players."PLAYER_ID"')
    return df

sql = 'select * from boxscore left join players on boxscore."PLAYER_ID" = players."PLAYER_ID"'

df = load_data(sql)

pts_input = st.sidebar.number_input("PTS: ", value = .5)
assist_input = st.sidebar.number_input("ASSTS: ", value = 2)
steals_input = st.sidebar.number_input("STLS: ", value = 3)
blocks_input = st.sidebar.number_input("BLKS: ", value = 3)
tov_input = st.sidebar.number_input("TOV: ", value = -2)
fgm_input = st.sidebar.number_input("FGM: ", value = 1)
fga_input = st.sidebar.number_input("FGA: ", value = -.45)
ftm_input = st.sidebar.number_input("FTM: ", value = 1)
fta_input = st.sidebar.number_input("FTA: ", value = -.75)
ft3m_input = st.sidebar.number_input("FG3M: ", value = 1.5)
orb_input = st.sidebar.number_input("OREB: ", value = 1.6)
drb_input = st.sidebar.number_input("DREB: ", value = 1.5)

df['fantasy_pts'] = (df['PTS']*pts_input + df['AST']*assist_input + df['STL']*steals_input + df['BLK']*blocks_input
                     + df['TOV']*tov_input + df['FGM']*fgm_input + df['FGA']*fga_input + df['FTM']*ftm_input
                     + df['FTA']*fta_input + df['FG3M']*ft3m_input + df['OREB']*orb_input + df['DREB']*drb_input)

df['cal_week'] = df['GAME_DATE'].map(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').isocalendar()[1])
df['year'] = df['GAME_DATE'].map(lambda x: x[:4])

fin = df.groupby(['Season', 'PLAYER_NAME', 'POSITION', 'cal_week', 'year']).agg({'fantasy_pts': ['min', 'median', 'max']}).reset_index()
fin.columns = ['Season', 'Player', 'Position', 'cal_week', 'year', 'Min', 'Median', 'Max']

dd = df[['Season','cal_week','year']].drop_duplicates()

dd['nba_week'] = dd.sort_values(['Season', 'year', 'cal_week'], ascending=[True, True, True]) \
             .groupby(['Season']) \
             .cumcount() + 1

final = fin.merge(dd, on = ['Season','cal_week','year'], how = 'left')[['Season', 'Player', 'Position', 'nba_week', 'Min', 'Median', 'Max']]
final.columns = ['Season', 'Player', 'Position', 'NBA Week', 'Min', 'Median', 'Max']

tab1, tab2 = st.tabs(["Week over Week Stats", "Season Ranks"])
with tab1:
    season_values = list(final['Season'].unique())
    season_default_ix = season_values.index('2022-23')
    season_option = st.selectbox(
        'Choose Season', season_values, season_default_ix
        )


    player_values = list(final['Player'].unique())
    player_default_ix = player_values.index('Russell Westbrook')
    player_option = st.selectbox(
        'Choose Player', player_values, player_default_ix
        )

    chart_df = final[(final['Player'] == player_option) & (final['Season'] == season_option)][['NBA Week', 'Min', 'Median', 'Max']]
    melt = chart_df.melt('NBA Week', var_name='Game Pick', value_name='Fantasy Points')

    st.line_chart(melt, x="NBA Week", y="Fantasy Points", color="Game Pick")

    chart_df['roll_min_pre'] = chart_df.sort_values('NBA Week')['Min'].rolling(5).mean().sort_index(ascending=True)
    chart_df['roll_median_pre'] = chart_df.sort_values('NBA Week')['Median'].rolling(5).mean().sort_index(ascending=True)
    chart_df['roll_max_pre'] = chart_df.sort_values('NBA Week')['Max'].rolling(5).mean().sort_index(ascending=True)

    chart_df['5 Week Rolling Min'] = chart_df.roll_min_pre.combine_first(chart_df.Min)
    chart_df['5 Week Rolling Median'] = chart_df.roll_median_pre.combine_first(chart_df.Median)
    chart_df['5 Week Rolling Max'] = chart_df.roll_max_pre.combine_first(chart_df.Max)
    chart_df_5 = chart_df[['NBA Week', '5 Week Rolling Min', '5 Week Rolling Median', '5 Week Rolling Max']]

    melt_5 = chart_df_5.melt('NBA Week', var_name='Game Pick', value_name='Fantasy Points')
    st.line_chart(melt_5, x="NBA Week", y="Fantasy Points", color="Game Pick")

with tab2:
    col1, col2, col3 = st.columns(3)

    with col1:
        season2_values = list(final['Season'].unique())
        season2_default_ix = season2_values.index('2022-23')
        season2_option = st.selectbox(
            'Choose Season ', season2_values, season2_default_ix
            )

    with col2:
        weeks_scored = st.number_input("Min Weeks Scored", value = 1)

    with col3:
        pos_values = ['All', 'G', 'G-F', 'F', 'F-C', 'C']
        pos_option = st.selectbox(
            'Choose Position', pos_values
            )

    if pos_option == 'All':
        season = final[final['Season'] == season2_option]
    elif pos_option != 'All':
        season = final[(final['Season'] == season2_option) & (final['Position'] == pos_option)]

    nice = st.slider('How nice are you at game pick?', 0, 100, 50)/100.0
    # weeks_scored = st.number_input("Min Weeks Scored", value = 1)

    if nice < .5:
        fir = season.groupby("Player").sample(frac = 1-nice/.5)
        sec = pd.concat([fir, season]).drop_duplicates(keep = False)

        tot = fir.groupby('Player')['Min'].sum() + sec.groupby('Player')['Min'].sum()
        cnt = fir.groupby('Player')['Min'].count() + sec.groupby('Player')['Min'].count()
        out = pd.DataFrame(tot/cnt)
        out['weeks'] = cnt
    elif nice == .50:
        out = pd.DataFrame(season.groupby('Player')['Median'].mean())
        out['weeks'] = season.groupby('Player')['Median'].count()
    elif nice == 0:
        out = pd.DataFrame(season.groupby('Player')['Min'].mean())
        out['weeks'] = season.groupby('Player')['Min'].count()
    elif nice == 1:
        out = pd.DataFrame(season.groupby('Player')['Max'].mean())
        out['weeks'] = season.groupby('Player')['Max'].count()
    elif nice > .5:
        fir = season.groupby("Player").sample(frac = 1-(nice-.5)/.5)
        sec = pd.concat([fir, season]).drop_duplicates(keep = False)

        tot = fir.groupby('Player')['Median'].sum() + sec.groupby('Player')['Max'].sum()
        cnt = fir.groupby('Player')['Median'].count() + sec.groupby('Player')['Max'].count()
        out = pd.DataFrame(tot/cnt)
        out['weeks'] = cnt

    out.reset_index(inplace = True)
    out.columns = ['Player','Fantasy Points', 'Weeks Counted']
    out_pre = out.merge(season[['Player', 'Position']].drop_duplicates(), on = ['Player'], how = 'left')
    out_fin = out_pre[out_pre['Weeks Counted'] >= weeks_scored]

    out_fin['Season Rank'] = out_fin['Fantasy Points'].rank(method='max', ascending = False)
    rnk = out_fin[~out_fin['Season Rank'].isnull()].sort_values('Season Rank')

    st.write(rnk[['Player', 'Position', 'Weeks Counted', 'Fantasy Points', 'Season Rank']].reset_index(drop = True))

    dash_pre = season.groupby('Player').agg({
        'Min':'mean',
        'Median':'mean',
        'Max':'mean',
        'NBA Week':'count'
    }).reset_index()

    dash = dash_pre[dash_pre['NBA Week'] >= weeks_scored]

    dash['Min Rank'] = dash['Min'].rank(method='max', ascending = False)
    dash['Median Rank'] = dash['Median'].rank(method='max', ascending = False)
    dash['Max Rank'] = dash['Max'].rank(method='max', ascending = False)

    dash['Delta Bad to Medium'] = dash['Min Rank'] - dash['Median Rank']
    dash['Delta Bad to Ok % Increase'] = dash['Delta Bad to Medium']/dash['Min Rank']
    dash['Delta Medium to Good'] = dash['Median Rank'] - dash['Max Rank']
    dash['Delta Ok to Elite % Increase'] = dash['Delta Medium to Good']/dash['Median Rank']
    dash['Delta Bad to Good'] = dash['Min Rank'] - dash['Median Rank']
    dash['Delta Bad to Elite % Increase'] = dash['Delta Bad to Good']/dash['Min Rank']

    rank_option = st.selectbox(
        'Choose Ordering', ('Best players if I go from bad picker to ok picker', 'Best players if I go from ok picker to elite picker'
        , 'Best players if I go from bad picker to elite picker', 'Best players if I go from elite picker to ok picker'
        , 'Best players if I go from ok picker to bad picker', 'Best player if I go from elite picker to bad picker'), 0
        )

    if rank_option == 'Best players if I go from bad picker to ok picker':
        st.write(dash.sort_values('Delta Bad to Ok % Increase', ascending = False)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Bad to Ok % Increase']].reset_index(drop = True).head(60))
    elif rank_option == 'Best players if I go from ok picker to elite picker':
        st.write(dash.sort_values('Delta Ok to Elite % Increase', ascending = False)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Ok to Elite % Increase']].reset_index(drop = True).head(60))
    elif rank_option == 'Best players if I go from bad picker to elite picker':
        st.write(dash.sort_values('Delta Bad to Elite % Increase', ascending = False)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Bad to Elite % Increase']].reset_index(drop = True).head(60))
    elif rank_option == 'Best players if I go from elite picker to ok picker':
        st.write(dash.sort_values('Delta Bad to Elite % Increase', ascending = True)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Bad to Elite % Increase']].reset_index(drop = True).head(60))
    elif rank_option == 'Best players if I go from ok picker to bad picker':
        st.write(dash.sort_values('Delta Bad to Ok % Increase', ascending = True)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Bad to Ok % Increase']].reset_index(drop = True).head(60))
    elif rank_option == 'Best player if I go from elite picker to bad picker':
        st.write(dash.sort_values('Delta Bad to Elite % Increase', ascending = True)[['Player', 'Min', 'Median', 'Max'
                        , 'Min Rank', 'Median Rank', 'Max Rank', 'Delta Bad to Elite % Increase']].reset_index(drop = True).head(60))
