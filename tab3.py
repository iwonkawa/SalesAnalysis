from dash import dcc, html
import plotly.graph_objects as go

def render_tab3(df):
    layout = html.Div([
        html.H1('Sales Channels', style={'text-align': 'center'}),
        html.Div([
            html.Label('Select Sales Channel:'),
            dcc.Dropdown(
                id='store-type-dropdown',
                options=[{'label': store_type, 'value': store_type} for store_type in df['Store_type'].unique()],
                value=df['Store_type'].unique()[0]
            )
        ], style={'width': '50%', 'margin': 'auto'}),

        html.Div([
            dcc.Graph(id='barh-sales-by-day')
        ])
    ])
    return layout