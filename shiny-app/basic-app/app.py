import altair as alt
import pandas as pd
import json
from shiny import App, ui, render
from shinywidgets import output_widget, render_altair

# load traffic crash data
traffic_crashes_map = pd.read_csv(
    '/Users/boyalin/Documents/GitHub/ppha30538_ps/ppha30538_final_project/shiny-app/traffic_crashes_map.csv'
)

# load GeoJSON data for Chicago neighborhoods
file_path = '/Users/boyalin/Documents/GitHub/ppha30538_ps/ppha30538_final_project/shiny-app/chicago_neighborhoods.geojson'
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson['features'])

# define function to filter data for a specific year
def filter_data_specific_year(category, year):
    if category == "All":
        filtered_data = traffic_crashes_map[
            (traffic_crashes_map['year'] == year)
        ]
    else:
        filtered_data = traffic_crashes_map[
            (traffic_crashes_map['category'] == category) & 
            (traffic_crashes_map['year'] == year)
        ]
    if filtered_data.empty:
        return pd.DataFrame(columns=['latitude_binned', 'longitude_binned', 'crash_count'])
    
    filtered_data = filtered_data.dropna(subset=['latitude_binned', 'longitude_binned', 'crash_count'])
    return filtered_data

# define function to filter data for a range of years
def filter_data_by_range(category, year_start, year_end):
    if category == "All":
        filtered_data = traffic_crashes_map[
            (traffic_crashes_map['year'] >= year_start) &
            (traffic_crashes_map['year'] <= year_end)
        ]
    else:
        filtered_data = traffic_crashes_map[
            (traffic_crashes_map['category'] == category) &
            (traffic_crashes_map['year'] >= year_start) &
            (traffic_crashes_map['year'] <= year_end)
        ]
    if filtered_data.empty:
        return pd.DataFrame(columns=['latitude_binned', 'longitude_binned', 'crash_count'])

    binned_data = filtered_data.groupby(['latitude_binned', 'longitude_binned']).agg({
        'crash_count': 'sum'}).reset_index()
    return binned_data

# dropdown choices with unique categories plus "All" option
dropdown_choices = ['All'] + traffic_crashes_map['category'].drop_duplicates().tolist()

# define UI
app_ui = ui.page_fluid(
    ui.tags.h1('Chicago Traffic Crashes Dashboard', style="font-size: 30px; color: #2c3e50; font-weight: bold; text-align: center;"),
    ui.input_select(
        'category_selector', 
        'Select Crash Causes:', 
        choices=dropdown_choices, 
        selected=dropdown_choices[0]
    ),
    ui.input_switch('switch_button', 'Toggle: Single Year or Year Range', value=False),
    ui.panel_conditional(
        '!input.switch_button',
        ui.input_slider(
            id='year_range', label='Select Year Range:', 
            min=2013, max=2024, value=[2013, 2024], step=1,
            animate=True, ticks=True,
            pre='', sep=''
        )
    ),
    ui.panel_conditional(
        'input.switch_button',
        ui.input_slider(
            id='single_year', label='Select Single Year:', 
            min=2013, max=2024, value=2016, step=1, 
            animate=True, ticks=True,
            pre='', sep=''
        )
    ),
    ui.row(
        ui.div(output_widget('traffic_crashes_plot', width=600), style="width: 48%; margin-right: 2%;"),
        ui.div(output_widget('time_series_plot', width=600), style="width: 48%;")
    )
)

# server Logic
def server(input, output, session):
    @output
    @render_altair
    def traffic_crashes_plot():
        selected_category = input.category_selector()
        
        if input.switch_button():
            selected_year = int(input.single_year())
            filtered_data = filter_data_specific_year(selected_category, selected_year)
        else:
            year_start, year_end = map(int, input.year_range())
            filtered_data = filter_data_by_range(selected_category, year_start, year_end)
        
        if filtered_data.empty:
            return alt.Chart(pd.DataFrame({'text': ['No data available']})).mark_text(
                align='center', baseline='middle', size=20
            ).encode(text='text:N').properties(
                title=f"No data available for {selected_category} in {selected_year}" if input.switch_button()
                else f"No data available for {selected_category} in {year_start}-{year_end}",
                width=600, height=600
            )
        
        lat_domain = [
            filtered_data['latitude_binned'].min() - 0.01, 
            filtered_data['latitude_binned'].max() + 0.01
        ]
        long_domain = [
            filtered_data['longitude_binned'].min() - 0.01, 
            filtered_data['longitude_binned'].max() + 0.01
        ]
        
        # map Layer
        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0, stroke='black', strokeWidth=0.6
        ).project(type='equirectangular').properties(width=600, height=600)
        
        # scatter Plot
        scatter_plot = alt.Chart(filtered_data).mark_circle().encode(
            x=alt.X('longitude_binned:Q', scale=alt.Scale(domain=long_domain), title='Longitude'),
            y=alt.Y('latitude_binned:Q', scale=alt.Scale(domain=lat_domain), title='Latitude'),
            size=alt.Size('crash_count:Q', scale=alt.Scale(range=[20, 300]), title='Crash Count'),
            color=alt.Color('crash_count:Q', scale=alt.Scale(range=['lightblue', 'darkblue']), title='Crash Count'),
            tooltip=['longitude_binned', 'latitude_binned', 'crash_count']
        ).properties(title=f'Traffic Crashes due to {selected_category if selected_category != "All" else "All Causes"}',
                     width=600, height=600)
        
        combined_plot = map_layer + scatter_plot
        return combined_plot
    

    @output
    @render_altair
    def time_series_plot():
        selected_category = input.category_selector()
        
        # only show time series when year range is selected
        if not input.switch_button(): 
            year_start, year_end = map(int, input.year_range())

            if selected_category == "All":
                # filter data for the year range
                time_series_data = traffic_crashes_map[
                    (traffic_crashes_map['year'] >= year_start) & 
                    (traffic_crashes_map['year'] <= year_end)
                ]
                # aggregate crash counts by year and category
                time_series_data = time_series_data.groupby(['year', 'category']).agg({'crash_count': 'sum'}).reset_index()
            else:
                # filter data for the selected category and year range
                time_series_data = traffic_crashes_map[
                    (traffic_crashes_map['category'] == selected_category) & 
                    (traffic_crashes_map['year'] >= year_start) & 
                    (traffic_crashes_map['year'] <= year_end)
                ]
                # aggregate crash counts by year
                time_series_data = time_series_data.groupby('year').agg({'crash_count': 'sum'}).reset_index()
                time_series_data['category'] = selected_category  # Add category for consistent encoding

            # check if data is available
            if time_series_data.empty:
                return alt.Chart(pd.DataFrame({'text': ['No data available']})).mark_text(
                    align='center', baseline='middle', size=20
                ).encode(text='text:N').properties(
                    title="No data available for the selected range",
                    width=600, height=400
                )

            # line chart
            line_chart = alt.Chart(time_series_data).mark_line(point=True).encode(
                x=alt.X('year:O', title='Year', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('crash_count:Q', title='Crash Count'),
                color=alt.Color('category:N', title='Crash Causes'),  # Color encoding for all or specific category
                tooltip=['year', 'category', 'crash_count']
            ).properties(
                title=f'Crash Counts Over Time ({selected_category if selected_category != "All" else "All Causes"})',
                width=500,
                height=500
            )
            return line_chart

# run the app
app = App(app_ui, server)

# ChatGPT reference for adding an option selecting all categories and display line chart by categories in this case
# ChatGPT reference for making two plots on the same page side by side