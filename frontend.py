import streamlit as st
from main import process_message

DB_LABELS = {
    "reserve_estimation": "Reserve Estimation Database",
    "demand_data":       "Power Demand Database",
    "dsm":               "DSM Rate Database",
}

def init_session():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def main():
    st.set_page_config(page_title="⚡ Power Analytics", layout="wide")
    init_session()

    st.sidebar.header("Select Data Sources")
    chosen = st.sidebar.multiselect(
        "Databases to query",
        options=list(DB_LABELS.values()),
        help="Check only the databases you want."
    )
    selected_dbs = [k for k,v in DB_LABELS.items() if v in chosen]

    st.title("⚡ Power Consumption Analyzer")
    st.markdown(
        "Select your data sources, ask a question, then refine the plan "
        "or say **go ahead** to execute."
    )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])

        if msg["role"] == "assistant" and "payload" in msg:
            payload = msg["payload"]
            # plan
            with st.expander("🔍 Generated Plan", expanded=False):
                st.code(payload["plan"], language="json")
            # explanations
            if payload.get("explanations"):
                st.markdown("💡 **Explanation:**")
                for e in payload["explanations"]:
                    st.markdown(f"- {e}")
            # errors
            if payload.get("errors"):
                st.markdown("⚠️ **Issues Found:**")
                for err in payload["errors"]:
                    st.error(err)
            # raw results
            if payload.get("raw_results") is not None:
                st.expander("▶ Raw DB Results", expanded=False).json(payload["raw_results"])
            # final answer
            if payload.get("answer"):
                st.markdown("✅ **Final Analysis:**")
                st.markdown(payload["answer"])
            elif payload.get("execute_ready"):
                st.info("Plan looks good—type **go ahead** and hit **Send** to run it.")

    # User input
    user_input = st.chat_input("Type your message here…")  
    if user_input:
        if not selected_dbs:
            st.error("Select at least one database in the sidebar.")
        else:
            st.session_state.chat_history.append({"role": "user", "text": user_input})
            with st.spinner("Thinking…"):
                resp = process_message(user_input, selected_dbs)
            assistant_text = "Here’s what I came up with:"
            st.session_state.chat_history.append({
                "role": "assistant",
                "text": assistant_text,
                "payload": resp
            })
        st.rerun()

if __name__ == "__main__":
    main()
