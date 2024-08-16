import pandas as pd
import datetime as dt
import os
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_auth
import plotly.graph_objects as go

# External stylesheets
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Authentication details
USERNAME_PASSWORD = [['user', 'pass']]

# Initialize Dash app
app = Dash(__name__, external_stylesheets=external_stylesheets)
#auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD)  # Set up basic authentication

class db:
    def __init__(self):
        self.transactions = self.transation_init()
        self.cc = pd.read_csv(r'C:\Kodilla\projekt\venv\db\country_codes.csv', index_col=0)
        self.customers = pd.read_csv(r'C:\Kodilla\projekt\venv\db\customers.csv', index_col=0)
        self.prod_info = pd.read_csv(r'C:\Kodilla\projekt\venv\db\prod_cat_info.csv')
        self.merged = self.merge()

    @staticmethod
    def transation_init():
        transactions_list = []
        src = r'C:\Kodilla\projekt\venv\db\transactions'
        for filename in os.listdir(src):
            transactions_list.append(pd.read_csv(os.path.join(src, filename), index_col=0))

        transactions = pd.concat(transactions_list)

        def convert_dates(x):
            try:
                return dt.datetime.strptime(x, '%d-%m-%Y')
            except:
                return dt.datetime.strptime(x, '%d/%m/%Y')

        transactions['tran_date'] = transactions['tran_date'].apply(lambda x: convert_dates(x))
        transactions['day_of_week'] = transactions['tran_date'].dt.day_name()

        return transactions

    def merge(self):
        df = self.transactions.join(
            self.prod_info.drop_duplicates(subset=['prod_cat_code'])
            .set_index('prod_cat_code')['prod_cat'], on='prod_cat_code', how='left'
        )

        df = df.join(
            self.prod_info.drop_duplicates(subset=['prod_sub_cat_code'])
            .set_index('prod_sub_cat_code')['prod_subcat'], on='prod_subcat_code', how='left'
        )

        df = df.join(
            self.customers.join(self.cc, on='country_code')
            .set_index('customer_Id'), on='cust_id'
        )

        return df

# Initialize and merge the data
db_instance = db()
df = db_instance.merged


# Define app layout
app.layout = html.Div([
    dcc.Tabs(id='tabs', value='tab-1', children=[
        dcc.Tab(label='Global Sales', value='tab-1'),
        dcc.Tab(label='Products', value='tab-2'),
        dcc.Tab(label='Sales Channels', value='tab-3')  
    ]),
    html.Div(id='tabs-content')
])

# Callback to render content based on the selected tab
@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return render_tab1(df)
    elif tab == 'tab-2':
        return render_tab2(df)
    elif tab == 'tab-3':
        return render_tab3(df)

@app.callback(Output('bar-sales', 'figure'),
              [Input('sales-range', 'start_date'), Input('sales-range', 'end_date')])
def tab1_bar_sales(start_date, end_date):
    truncated = df[(df['tran_date'] >= start_date) & (df['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby(
        [pd.Grouper(key='tran_date', freq='ME'), 'Store_type']
    )['total_amt'].sum().round(2).unstack()

    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(
            x=grouped.index, y=grouped[col], name=col, hoverinfo='text',
            hovertext=[f'{y/1e3:.2f}k' for y in grouped[col].values]
        ))

    fig = go.Figure(data=traces, layout=go.Layout(
        title='Revenue', barmode='stack', legend=dict(x=0, y=-0.5)
    ))

    return fig
    
@app.callback(Output('choropleth-sales','figure'),
              [Input('sales-range','start_date'), Input('sales-range','end_date')])
def tab1_choropleth_sales(start_date, end_date):
    truncated = df[(df['tran_date'] >= start_date) & (df['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby('country')['total_amt'].sum().round(2)

    trace0 = go.Choropleth(colorscale='Viridis', reversescale=True,
                           locations=grouped.index, locationmode='country names',
                           z=grouped.values, colorbar=dict(title='Sales'))
    data = [trace0]
    fig = go.Figure(data=data, layout=go.Layout(
        title='Sales Map', geo=dict(showframe=False, projection={'type':'natural earth'})))

    return fig

# Callback for tab 2: Bar chart
@app.callback(Output('barh-prod-subcat', 'figure'),
              [Input('prod_dropdown', 'value')])
def tab2_barh_prod_subcat(chosen_cat):
    grouped = df[(df['total_amt'] > 0) & (df['prod_cat'] == chosen_cat)] \
        .pivot_table(index='prod_subcat', columns='Gender', values='total_amt', aggfunc='sum') \
        .assign(_sum=lambda x: x['F'] + x['M']).sort_values(by='_sum').round(2)

    traces = []
    for col in ['F', 'M']:
        traces.append(go.Bar(x=grouped[col], y=grouped.index, orientation='h', name=col))

    fig = go.Figure(data=traces, layout=go.Layout(barmode='stack', margin={'t': 20}))
    return fig

# Callback for tab 3: Sales by day and store type
@app.callback(Output('barh-sales-by-day', 'figure'),
              [Input('store-type-dropdown', 'value')])
def tab3_sales_by_day(store_type):
    filtered = df[df['Store_type'] == store_type]
    grouped = filtered.groupby('day_of_week')['total_amt'].sum().reindex(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    )
    
    fig = go.Figure(
        data=[go.Bar(x=grouped.index, y=grouped.values)],
        layout=go.Layout(title=f'Sales by Day of Week for {store_type}', yaxis=dict(title='Total Sales'))
    )
    return fig

# Run the Dash app in Jupyter Notebook
app.run_server(mode='inline', port=8055)
