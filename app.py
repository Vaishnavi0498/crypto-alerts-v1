import streamlit as st
import pandas as pd

from price_cache import (
    get_prices,
    get_price
)

from database import (
    init_db,
    create_alert,
    get_active_alerts,
    get_history,
    delete_alert,
    reset_alert,
    active_alert_count,
    triggered_alert_count,
    history_count,
    get_monitored_symbols,
    update_alert,
    update_state
)

from symbol_service import (
    get_symbols
)

from streamlit_autorefresh import st_autorefresh

init_db()


def format_price(price):

    if price is None:
        return "-"

    if price >= 1000:
        return f"{price:.2f}"

    elif price >= 1:
        return f"{price:.4f}"

    elif price >= 0.01:
        return f"{price:.5f}"

    else:
        return f"{price:.8f}"


st.set_page_config(
    page_title="Crypto Alert Center",
    layout="wide"
)

st_autorefresh(
    interval=5000,
    key="refresh"
)

st.title("🚀 Crypto Alert Center")

# -----------------------------------
# DASHBOARD
# -----------------------------------

st.header("Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Active Alerts",
        active_alert_count()
    )

with col2:
    st.metric(
        "Triggered Alerts",
        triggered_alert_count()
    )

with col3:
    st.metric(
        "History Entries",
        history_count()
    )

with col4:
    st.metric(
        "Monitored Symbols",
        len(get_monitored_symbols())
    )

# -----------------------------------
# LIVE PRICES
# -----------------------------------

st.header("📈 Live Prices")

prices = get_prices()

if prices:

    formatted_prices = []

    for symbol, price, updated_at in prices:

        formatted_prices.append(
            (
                symbol,
                format_price(price),
                updated_at
            )
        )

    prices_df = pd.DataFrame(
        formatted_prices,
        columns=[
            "Symbol",
            "Price",
            "Updated At"
        ]
    )

    st.dataframe(
        prices_df,
        use_container_width=True
    )

else:

    st.info(
        "Waiting for market data..."
    )

# -----------------------------------
# CREATE ALERT
# -----------------------------------

st.header("Create Alert")

symbols = get_symbols()

with st.form("alert_form"):

    symbol = st.selectbox(
        "Symbol",
        symbols
    )

    condition = st.selectbox(
        "Condition",
        [">", "<"]
    )

    target_price = st.number_input(
        "Target Price",
        min_value=0.0,
        format="%.8f"
    )

    alert_type = st.selectbox(
        "Alert Type",
        [
            "one_time",
            "recurring"
        ]
    )

    notes = st.text_area(
        "Analysis Notes"
    )

    submitted = st.form_submit_button(
        "Create Alert"
    )

    if submitted:

        alert_id = create_alert(
            symbol,
            condition,
            target_price,
            alert_type,
            notes
        )

        current_price = get_price(
            symbol
        )

        if current_price is not None:

            current_state = (
                "ABOVE"
                if current_price >= target_price
                else "BELOW"
            )

            update_state(
                alert_id,
                current_state
            )

        st.success(
            "Alert Created"
        )

        st.rerun()

search_symbol = st.text_input(
    "Search Alerts",
    ""
).upper()

# -----------------------------------
# ACTIVE ALERTS
# -----------------------------------

st.header("🟢 Active Alerts")

active_alerts = get_active_alerts()

if active_alerts:

    for row in active_alerts:

        if (
            search_symbol
            and search_symbol not in row[1]
        ):
            continue

        (
            alert_id,
            symbol,
            condition,
            target_price,
            alert_type,
            notes,
            active,
            triggered_count,
            last_state,
            created_at,
            last_triggered_at
        ) = row

        with st.expander(
            f"{symbol} {condition} {format_price(target_price)}"
        ):

            edit_mode = st.checkbox(
                "Edit",
                key=f"edit_{alert_id}"
            )

            if edit_mode:

                new_condition = st.selectbox(
                    "Condition",
                    [">", "<"],
                    index=0 if condition == ">" else 1,
                    key=f"cond_{alert_id}"
                )

                new_target = st.number_input(
                    "Target Price",
                    value=float(target_price),
                    format="%.8f",
                    key=f"target_{alert_id}"
                )

                new_type = st.selectbox(
                    "Alert Type",
                    ["one_time", "recurring"],
                    index=0 if alert_type == "one_time" else 1,
                    key=f"type_{alert_id}"
                )

                new_notes = st.text_area(
                    "Notes",
                    value=notes or "",
                    key=f"notes_{alert_id}"
                )

                if st.button(
                    f"Save {alert_id}",
                    key=f"save_{alert_id}"
                ):

                    update_alert(
                        alert_id,
                        new_condition,
                        new_target,
                        new_type,
                        new_notes
                    )

                    st.success(
                        "Alert Updated"
                    )

                    st.rerun()

            else:

                current_price = get_price(
                    symbol
                )

                if current_price is not None:

                    pct_diff = (
                        (current_price - target_price)
                        / target_price
                    ) * 100

                    st.write(
                        f"Distance: {pct_diff:.2f}%"
                    )

                    st.write(
                        f"Current Price: {format_price(current_price)}"
                    )

                st.write(
                    f"Type: {alert_type}"
                )

                st.write(
                    f"Triggered Count: {triggered_count}"
                )

                st.write(
                    notes
                )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    f"Delete {alert_id}",
                    key=f"delete_{alert_id}"
                ):

                    delete_alert(
                        alert_id
                    )

                    st.rerun()

            with col2:

                if st.button(
                    f"Reset {alert_id}",
                    key=f"reset_{alert_id}"
                ):

                    reset_alert(
                        alert_id
                    )

                    st.rerun()

else:

    st.info(
        "No active alerts"
    )

# -----------------------------------
# TRIGGER HISTORY
# -----------------------------------

st.header("🔔 Trigger History")

history = get_history()

if history:

    history_df = pd.DataFrame(
        history,
        columns=[
            "History ID",
            "Alert ID",
            "Symbol",
            "Trigger Price",
            "Notes",
            "Triggered At"
        ]
    )

    history_df = history_df[
        [
            "Symbol",
            "Trigger Price",
            "Triggered At",
            "Notes"
        ]
    ]

    history_df["Trigger Price"] = (
    history_df["Trigger Price"]
    .apply(format_price)
)

    st.dataframe(
        history_df,
        use_container_width=True
    )

else:

    st.info(
        "No triggered alerts yet"
    )