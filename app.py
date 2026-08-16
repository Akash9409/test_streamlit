import streamlit as st
import snowflake.connector
import pandas as pd


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="Customer Data Editor",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# Snowflake connection
# =========================================================

@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )


# =========================================================
# Load table
# =========================================================

def load_customers():

    conn = get_connection()

    query = """
        SELECT
            ID,
            NAME,
            EMAIL,
            STATUS
        FROM STREAMLIT_EXCEL_APP.DATA.CUSTOMERS
        ORDER BY ID
    """

    return pd.read_sql(query, conn)


# =========================================================
# Initialize data
# =========================================================

if "customers" not in st.session_state:

    st.session_state.customers = load_customers()


# =========================================================
# Header
# =========================================================

st.title("📊 Customer Data")

st.caption(
    "Edit cells, copy/paste from Excel, add rows, or delete rows."
)


# =========================================================
# Data editor
# =========================================================

edited_df = st.data_editor(
    st.session_state.customers,
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    height=600,

    column_config={
        "ID": st.column_config.NumberColumn(
            "ID",
            help="Unique customer ID",
            min_value=1,
            step=1,
        ),

        "NAME": st.column_config.TextColumn(
            "Name",
        ),

        "EMAIL": st.column_config.TextColumn(
            "Email",
        ),

        "STATUS": st.column_config.TextColumn(
            "Status",
        ),
    },

    key="customer_editor",
)


# =========================================================
# Save / discard
# =========================================================

st.divider()

col1, col2 = st.columns([1, 1])


with col1:

    if st.button(
        "💾 Save Changes",
        type="primary",
    ):

        st.info(
            "Snowflake save logic will be implemented next."
        )


with col2:

    if st.button("↩️ Discard Changes"):

        st.session_state.customers = load_customers()

        # Clear the editor's widget state so it reloads
        # from Snowflake.
        if "customer_editor" in st.session_state:
            del st.session_state.customer_editor

        st.rerun()
