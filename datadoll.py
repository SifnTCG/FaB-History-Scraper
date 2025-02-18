import dash
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

# Load your CSV data
file_path = 'match_history.csv'  # Replace with your CSV file path
data = pd.read_csv(file_path)

# Concatenate 'Player 1' and 'Player 2' columns and find the most frequent player
all_players = pd.concat([data['Player 1'], data['Player 2']])
user_name = all_players.value_counts().idxmax()  # Most frequent name in all matches
total_matches = len(data)

# Determine opponent names and whether the user won each match
data['Opponent'] = data.apply(lambda row: row['Player 2'] if row['Player 1'] == user_name else row['Player 1'], axis=1)
data['User_Win'] = ((data['Player 1'] == user_name) & data['Result'].str.contains('Player 1 Win')) | \
                   ((data['Player 2'] == user_name) & data['Result'].str.contains('Player 2 Win'))

# Total winrate
total_winrate = data['User_Win'].mean()

# Winrate as Player 1 and Player 2
data['User_Is_Player1'] = data['Player 1'] == user_name
data['User_Is_Player2'] = data['Player 2'] == user_name
winrate_player1 = data[data['User_Is_Player1']]['User_Win'].mean()
winrate_player2 = data[data['User_Is_Player2']]['User_Win'].mean()

# Group data by opponent and calculate win rate
opponent_win_rate = data.groupby('Opponent')['User_Win'].mean().reset_index()
opponent_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)

# Calculate match count, win count, and loss count against each opponent
opponent_stats = data.groupby('Opponent').agg(
    Match_Count=('Opponent', 'size'),
    Win_Count=('User_Win', lambda x: x.sum()),  # Count the wins
    Loss_Count=('User_Win', lambda x: (1-x).sum())  # Count the losses
).reset_index()

# Calculate win rate for later use
opponent_stats['Win_Rate'] = opponent_stats['Win_Count'] / opponent_stats['Match_Count']

# Sort opponents by win rate
opponent_win_rate_sorted = opponent_win_rate.sort_values('Win Rate', ascending=True)

top_5_opponents = opponent_stats.nlargest(5, 'Match_Count')
number_opponents = len(opponent_stats)

# Group data by round and calculate win rate
round_win_rate = data.groupby('Round')['User_Win'].mean().reset_index()
round_win_rate.rename(columns={'User_Win': 'Win Rate'}, inplace=True)

round_win_rate['Win Rate'] = round_win_rate['Win Rate'] * 100

# Create the figure
round_win_rate_figure = px.bar(round_win_rate, x='Round', y='Win Rate', title='Win Rate per Round')

# Update hover template to show percentage
round_win_rate_figure.update_traces(hovertemplate='Round %{x}<br>Win Rate=%{y:.2f}%')
round_win_rate_figure.update_layout(yaxis_title="Win Rate (%)")

# Assuming top_5_opponents is already sorted by 'Match_Count' descending
fig = go.Figure()
fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent'],
    y=top_5_opponents['Win_Count'],
    name='Wins',
    marker_color='#6495ED'
))
fig.add_trace(go.Bar(
    x=top_5_opponents['Opponent'],
    y=top_5_opponents['Loss_Count'],
    name='Losses',
    marker_color='#FF7F24'
))

# Modify the layout to stack the bars
fig.update_layout(
    barmode='stack',
    title='Top 5 Opponents by Match Count',
    xaxis_title='Opponent',
    yaxis_title='Count'
)

fig_win_rate = px.bar(
    opponent_win_rate_sorted,
    x='Win Rate',
    y='Opponent',
    orientation='h',
    title='Win Rate Against Each Opponent'
)
fig_win_rate.update_layout(yaxis={'categoryorder': 'total ascending'}, xaxis_title="Win Rate (%)")
fig_win_rate.update_traces(marker_color='cyan')


# Additional Data processing here

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div([
    html.H1('FaB History Analysis'),
    html.Div('Interactive visualization of matchup history.'),

    html.Div([
        dcc.RadioItems(
            id='rating_filter',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': 'True'},
                {'label': 'Unrated', 'value': 'False'}
            ],
            value='all',  # Default value
            labelStyle={'display': 'inline-block'}
        ),
        html.Div(id='stats_output')  # Div to display updated stats
    ]),

    html.Div([
        dcc.Input(id='opponent_name_input', type='text', placeholder='Enter opponent name'),
        html.Button('Submit', id='opponent_name_submit'),
        html.Div(id='opponent_name_output')
    ]),


    dcc.Dropdown(
        id='sort_by_dropdown',
        options=[
            {'label': 'Name - Ascending', 'value': 'Name_asc'},
            {'label': 'Name - Descending', 'value': 'Name_desc'},
            {'label': 'Win Rate - Ascending', 'value': 'Win Rate_asc'},
            {'label': 'Win Rate - Descending', 'value': 'Win Rate_desc'}
        ],
        value='Name_asc'
    ),
    html.Div([
        dcc.RadioItems(
            id='rated_filter',
            options=[
                {'label': 'All', 'value': 'all'},
                {'label': 'Rated', 'value': True},
                {'label': 'Unrated', 'value': False}
            ],
            value='all',  # Default value
            labelStyle={'display': 'inline-block'}
        ),
    ]),
    dcc.Graph(id='filtered_graph', figure=fig_win_rate),

    dcc.Graph(id='top-opponents-graph', figure=fig),

    dcc.Graph(figure=round_win_rate_figure)

])


@app.callback(
    Output('filtered_graph', 'figure'),
    [Input('sort_by_dropdown', 'value'), Input('rated_filter', 'value')]
)
def update_graph(sort_by_value, rated_value):
    # Filter by rated status if not 'all'
    if rated_value != 'all':
        filtered_data = data[data['Rated'] == rated_value]
    else:
        filtered_data = data.copy()

    # Group by opponent and calculate win rate and match count
    opponent_stats_filtered = filtered_data.groupby('Opponent').agg(
        Match_Count=('Opponent', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()

    # Convert 'Win_Rate' to percentage
    opponent_stats_filtered['Win_Rate'] *= 100

    # Determine sorting
    sort_by, order = sort_by_value.split('_')
    ascending = order == 'asc'

    if sort_by == 'Name':
        opponent_stats_filtered.sort_values(by='Opponent', ascending=ascending, inplace=True)
    elif sort_by == 'Win Rate':
        opponent_stats_filtered.sort_values(by='Win_Rate', ascending=ascending, inplace=True)

    # Create the figure
    figure = px.bar(
        opponent_stats_filtered,
        x='Opponent',
        y='Win_Rate',
        title='Win Rate Against Each Opponent'
    )

    # Update hover template to show percentage and match count
    figure.update_traces(
        hovertemplate='Opponent: %{x}<br>Win Rate: %{y:.2f}%<br>Match Count: %{customdata}'
    )
    figure.update_layout(yaxis_title="Win Rate (%)")

    # Add customdata for hover info
    figure.update_traces(customdata=opponent_stats_filtered['Match_Count'])

    return figure


@app.callback(
    Output('opponent_name_output', 'children'),
    [Input('opponent_name_submit', 'n_clicks')],
    [State('opponent_name_input', 'value')]
)
def update_output(n_clicks, value):
    if n_clicks is None or value is None:
        return 'Enter an opponent name and click submit'

    # Replace NaN values in 'Opponent' column and filter data
    filtered_data = data[data['Opponent'].fillna('').str.contains(value, case=False)]

    if filtered_data.empty:
        return 'No matches found for this opponent'

    # Group by 'Opponent' and calculate win rate and count for each
    opponent_stats = filtered_data.groupby('Opponent').agg(
        Match_Count=('Opponent', 'size'),
        Win_Rate=('User_Win', 'mean')
    ).reset_index()

    # Formatting the output
    results = []
    for index, row in opponent_stats.iterrows():
        results.append(f"{row['Opponent']}: {row['Match_Count']} matches, {row['Win_Rate']:.2%} win rate")

    return html.Ul([html.Li(opponent) for opponent in results])


@app.callback(
    Output('stats_output', 'children'),
    [Input('rating_filter', 'value')]
)
def update_stats(rating_filter):
    if rating_filter == 'all':
        filtered_data = data
    elif rating_filter == 'True':
        filtered_data = data[data['Rated'] == True]
    else:
        filtered_data = data[data['Rated'] == False]

    total_matches = len(filtered_data)
    total_winrate = filtered_data['User_Win'].mean()
    winrate_player1 = filtered_data[filtered_data['User_Is_Player1']]['User_Win'].mean()
    winrate_player2 = filtered_data[filtered_data['User_Is_Player2']]['User_Win'].mean()
    number_opponents = len(filtered_data.groupby('Opponent'))

    return html.Div([
        html.H3(f'Total Matches: {total_matches}'),
        html.H3(f'Total Winrate: {total_winrate:.2%}'),
        html.H3(f'Winrate as Player 1: {winrate_player1:.2%}'),
        html.H3(f'Winrate as Player 2: {winrate_player2:.2%}'),
        html.H3(f'Number of different Opponents: {number_opponents}')
    ])


# Run the app
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)
