import streamlit as st
import snowflake.connector
import pandas as pd

from st_aggrid import (
    AgGrid,
    GridOptionsBuilder,
    GridUpdateMode,
    DataReturnMode,
)

st.set_page_config(
    page_title="Snowflake Data Editor",
    page_icon="📊",
    layout="wide",
)

st.title("Snowflake Data Editor")


# ---------------------------------------------------------
# Snowflake connection
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

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


df = load_customers()


# ---------------------------------------------------------
# Display table
# ---------------------------------------------------------

st.subheader("Customers")

st.write(
    "You can edit cells directly, copy/paste multiple cells, "
    "and add/delete rows."
)


gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_default_column(
    editable=True,
    resizable=True,
    sortable=True,
    filter=True,
)

gb.configure_column(
    "ID",
    editable=True,
)

gb.configure_column(
    "NAME",
    editable=True,
)

gb.configure_column(
    "EMAIL",
    editable=True,
)

gb.configure_column(
    "STATUS",
    editable=True,
)

gb.configure_grid_options(
    enableRangeSelection=True,
    enableClipboard=True,
    suppressClipboardPaste=False,
)

gb.configure_selection(
    selection_mode="multiple",
    use_checkbox=True,
)

grid_options = gb.build()


response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=500,
)

edited_df = response["data"]


# ---------------------------------------------------------
# Temporary debug output
# ---------------------------------------------------------

st.subheader("Current Grid Data")

st.dataframe(
    edited_df,
    use_container_width=True,
)
