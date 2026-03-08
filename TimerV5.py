import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.title("📊 WhatsApp Reply Time Analyzer")

uploaded_file = st.file_uploader("Upload WhatsApp Chat TXT", type=["txt"])

threshold_minutes = st.slider(
    "Reply Time Threshold (minutes)",
    min_value=1,
    max_value=60,
    value=5
)

if uploaded_file:

    text = uploaded_file.read().decode("utf-8")

    data = []

    for line in text.splitlines():
        # Try standard WhatsApp format first: [DD/MM/YYYY, HH:MM:SS AM/PM] Sender: Message
        match = re.match(r"\[(.*?)\] (.*?): (.*)", line)
        
        if match:
            timestamp, sender, message = match.groups()
            try:
                time_obj = datetime.strptime(timestamp, "%d/%m/%Y, %I:%M:%S %p")
                data.append({
                    "time": time_obj,
                    "sender": sender,
                    "message": message
                })
            except:
                continue
        else:
            # Try alternative format: YYYY/MM/DD HH:MM - Sender: Message
            match = re.match(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}) - (.*?): (.*)", line)
            if match:
                timestamp, sender, message = match.groups()
                try:
                    time_obj = datetime.strptime(timestamp, "%Y/%m/%d %H:%M")
                    data.append({
                        "time": time_obj,
                        "sender": sender,
                        "message": message
                    })
                except:
                    continue

    df = pd.DataFrame(data)

    if df.empty:
        st.warning("No valid messages detected.")
        st.stop()

    df = df.sort_values("time").reset_index(drop=True)

    # -----------------------
    # REPLY CALCULATION
    # -----------------------

    reply_data = []

    for i in range(1, len(df)):

        if df.loc[i, "sender"] != df.loc[i-1, "sender"]:

            diff = df.loc[i, "time"] - df.loc[i-1, "time"]

            reply_data.append({
                "from": df.loc[i-1, "sender"],
                "to": df.loc[i, "sender"],
                "reply_seconds": diff.total_seconds(),
                "reply_minutes": diff.total_seconds() / 60,
                "msg_index": i-1,
                "reply_index": i
            })

    reply_df = pd.DataFrame(reply_data)

    if reply_df.empty:
        st.warning("No reply interactions detected. This might happen if all messages are from the same sender or if the chat format isn't recognized.")
        st.stop()

    threshold_seconds = threshold_minutes * 60
    reply_df["within_threshold"] = reply_df["reply_seconds"] <= threshold_seconds

    # -----------------------
    # METRICS
    # -----------------------

    st.subheader("📈 Reply Performance Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Average Reply Time (min)",
        round(reply_df["reply_minutes"].mean(), 2)
    )

    col2.metric(
        "Median Reply Time (min)",
        round(reply_df["reply_minutes"].median(), 2)
    )

    col3.metric(
        "Within Threshold %",
        f"{round(reply_df['within_threshold'].mean()*100,2)}%"
    )

    # -----------------------
    # REPLY DATA TABLE
    # -----------------------

    st.subheader("📊 Reply Data")

    st.dataframe(reply_df)

    # Select row to inspect
    row_options = [f"Row {i}: {row['from']} -> {row['to']} ({row['reply_minutes']:.2f} min)" for i, row in reply_df.iterrows()]
    selected_option = st.selectbox("Select a reply to inspect context", [""] + row_options)

    # -----------------------
    # CHAT PREVIEW
    # -----------------------

    if selected_option:
        selected_row = int(selected_option.split(":")[0].replace("Row ", ""))

        msg_idx = reply_df.iloc[selected_row]["msg_index"]
        reply_idx = reply_df.iloc[selected_row]["reply_index"]

        # define context window
        start = max(msg_idx - 3, 0)
        end = min(reply_idx + 10, len(df) - 1)

        preview_df = df.loc[start:end]

        st.subheader("💬 Conversation Context")

        for i, row in preview_df.iterrows():

            if i == msg_idx:
                st.markdown(
                    f"🟦 **MESSAGE**  \n"
                    f"**{row['sender']}** | {row['time']}  \n"
                    f"{row['message']}"
                )

            elif i == reply_idx:
                st.markdown(
                    f"🟩 **REPLY**  \n"
                    f"**{row['sender']}** | {row['time']}  \n"
                    f"{row['message']}"
                )

            else:
                st.markdown(
                    f"**{row['sender']}** | {row['time']}  \n"
                    f"{row['message']}"
                )