from database import (
    get_active_alerts,
    update_state,
    mark_triggered,
    deactivate_alert,
    add_history
)
import time

RECURRING_COOLDOWN_SECONDS = 10 * 60  # 10 minutes


def evaluate_alerts(
    symbol,
    current_price
):

    events = []

    alerts = get_active_alerts()

    for alert in alerts:

        (
            alert_id,
            alert_symbol,
            condition,
            target_price,
            alert_type,
            notes,
            active,
            triggered_count,
            last_state,
            created_at,
            last_triggered_at
        ) = alert

        if alert_symbol != symbol:
            continue

        # -------------------
        # State Calculation
        # -------------------

        current_state = (
            "ABOVE"
            if current_price >= target_price
            else "BELOW"
        )

        # -------------------
        # First Observation
        # -------------------

        if last_state is None:

            update_state(
                alert_id,
                current_state
            )

            continue

        should_trigger = False

        # -------------------
        # Cross Above
        # -------------------

        if condition == ">":

            if (
                last_state == "BELOW"
                and current_state == "ABOVE"
            ):
                should_trigger = True

        # -------------------
        # Cross Below
        # -------------------

        elif condition == "<":

            if (
                last_state == "ABOVE"
                and current_state == "BELOW"
            ):
                should_trigger = True

        # -------------------
        # Trigger Handling
        # -------------------

        if should_trigger:

            # Cooldown for recurring alerts
            if (
                alert_type == "recurring"
                and last_triggered_at is not None
            ):
                # If last_triggered_at is a datetime object
                if hasattr(last_triggered_at, "timestamp"):
                    elapsed = time.time() - last_triggered_at.timestamp()
                else:
                    # If it is already stored as a Unix timestamp
                    elapsed = time.time() - float(last_triggered_at)

                if elapsed < RECURRING_COOLDOWN_SECONDS:
                    print(
                        f"Skipping recurring alert for {symbol} "
                        f"(cooldown {elapsed:.1f}s < {RECURRING_COOLDOWN_SECONDS}s)"
                    )

                    # Still update state before continuing
                    update_state(
                        alert_id,
                        current_state
                    )

                    continue

            print(
                "TRIGGERING",
                alert_id,
                alert_symbol,
                condition,
                current_price,
                target_price,
                last_state,
                current_state
            )

            mark_triggered(
                alert_id
            )

            add_history(
                alert_id,
                symbol,
                current_price,
                notes
            )

            if alert_type == "one_time":

                deactivate_alert(
                    alert_id
                )

            events.append(
                {
                    "alert_id": alert_id,
                    "symbol": symbol,
                    "price": current_price,
                    "notes": notes,
                    "type": alert_type
                }
            )

        # -------------------
        # Save New State
        # -------------------

        update_state(
            alert_id,
            current_state
        )

    return events