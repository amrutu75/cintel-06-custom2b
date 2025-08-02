import faicons as fa
import plotly.express as px
import pandas as pd
from pathlib import Path

from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly
import random 
from datetime import datetime

# -----------------------------
# Constants
# -----------------------------
UPDATE_INTERVAL_SECS = 1

#Load tips.csv from the same directory as this script
TIPS_PATH = Path(__file__).parent / "tips.csv"

# -----------------------------
# Reactive CSV Loader
# -----------------------------
@reactive.calc
def read_tips():
    return pd.read_csv(TIPS_PATH)

# Load once for min/max bill
tips_static = pd.read_csv(TIPS_PATH)
bill_rng = (tips_static.total_bill.min(), tips_static.total_bill.max())

ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "currency-dollar": fa.icon_svg("dollar-sign"),
    "ellipsis": fa.icon_svg("ellipsis"),
}

# UI layout
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider("total_bill", "Bill amount", min=bill_rng[0], max=bill_rng[1], value=bill_rng, pre="$"),
        ui.input_checkbox_group("time", "Food service", ["Lunch", "Dinner"], selected=["Lunch", "Dinner"], inline=True),
        ui.input_action_button("reset", "Reset filter"),
        open="desktop",
    ),
    ui.layout_columns(
        ui.value_box("Total tippers", ui.output_ui("total_tippers"), showcase=ICONS["user"]),
        ui.value_box("Average tip", ui.output_ui("average_tip"), showcase=ICONS["wallet"]),
        ui.value_box("Average bill", ui.output_ui("average_bill"), showcase=ICONS["currency-dollar"]),
        ui.value_box("Live Tip Update", ui.output_ui("live_tip_value"), showcase=ICONS["wallet"]),  # ✅ Added here
        fill=False,
    ),
    ui.layout_columns(
        ui.card(ui.card_header("Tips data"), ui.output_data_frame("table"), full_screen=True),
        ui.card(
            ui.card_header(
                "Total bill vs tip",
                ui.popover(
                    ICONS["ellipsis"],
                    ui.input_radio_buttons(
                        "scatter_color", None, ["none", "sex", "smoker", "day", "time"], inline=True
                    ),
                    title="Add a color variable",
                    placement="top",
                ),
                class_="d-flex justify-content-between align-items-center",
            ),
            output_widget("scatterplot"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header(
                "Tip percentages",
                ui.popover(
                    ICONS["ellipsis"],
                    ui.input_radio_buttons(
                        "tip_perc_y",
                        "Split by:",
                        ["sex", "smoker", "day", "time"],
                        selected="day",
                        inline=True,
                    ),
                    title="Add a color variable",
                ),
                class_="d-flex justify-content-between align-items-center",
            ),
            output_widget("tip_perc"),
            full_screen=True,
        ),
        col_widths=[6, 6, 12],
    ),
    title="Mt. Kilimanjaro Restaurant Tipping Dashboard",
    fillable=True,
)

# Server logic
def server(input, output, session):
    @reactive.calc
    def tips_data():
        d = read_tips()
        bill = input.total_bill()
        idx1 = d.total_bill.between(bill[0], bill[1])
        idx2 = d.time.isin(input.time())
        return d[idx1 & idx2]


    @render.ui
    def total_tippers():
        return tips_data().shape[0]

    @render.ui
    def average_tip():
        d = tips_data()
        if d.shape[0] > 0:
            perc = d.tip / d.total_bill
            return f"{perc.mean():.1%}"

    @render.ui
    def average_bill():
        d = tips_data()
        if d.shape[0] > 0:
            bill = d.total_bill.mean()
            return f"${bill:.2f}"

    @render.data_frame
    def table():
        return render.DataGrid(tips_data())

    @render_plotly
    def scatterplot():
        data = tips_data()
        if data.empty:
            return go.Figure()
        color = input.scatter_color()
        return px.scatter(
            data,
            x="total_bill",
            y="tip",
            color=None if color == "none" else color,
            trendline="lowess",
        )

    @render_plotly
    def tip_perc():
        dat = tips_data().copy()
        dat["percent"] = dat.tip / dat.total_bill
        yvar = input.tip_perc_y()
        fig = px.histogram(
            dat,
            x="percent",
            color=yvar,
            nbins=30,
            barmode="overlay",
            opacity=0.7,
            labels={"percent": "Tip Percentage"},
            title="Distribution of Tip Percentage",
        )
        fig.update_layout(
            xaxis_tickformat=".0%",
            legend_title_text=yvar,
            bargap=0.1,
        )
        return fig

    @reactive.effect
    @reactive.event(input.reset)
    def _():
        ui.update_slider("total_bill", value=bill_rng)
        ui.update_checkbox_group("time", selected=["Lunch", "Dinner"])

    # 1-second reactive live data generator
    @reactive.calc()
    def reactive_calc_generate_data():
        reactive.invalidate_later(UPDATE_INTERVAL_SECS)
        tips_val = round(random.uniform(-20, 35), 2)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"tips": tips_val, "timestamp": timestamp}

    # Live tip display
    @render.ui
    def live_tip_value():
        data = reactive_calc_generate_data()
        return f"Live Tip: {data['tips']} at {data['timestamp']}"


app = App(app_ui, server)
