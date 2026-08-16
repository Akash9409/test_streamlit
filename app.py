import streamlit as st
import snowflake.connector
import pandas as pd
import uuid

from st_aggrid import (
    AgGrid,
    GridOptionsBuilder,
    GridUpdateMode,
    DataReturnMode,
)

# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="Snowflake Data Editor",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Snowflake Data Editor")


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
# Load customers from Snowflake
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

    df = pd.read_sql(query, conn)

    return df


# =========================================================
# Add internal row identifier
# =========================================================

def add_row_keys(df):

    df = df.copy()

    df["_row_key"] = [
        str(uuid.uuid4())
        for _ in range(len(df))
    ]

    return df


# =========================================================
# Initialize session state
# =========================================================

if "customers_df" not in st.session_state:

    df = load_customers()

    st.session_state.customers_df = add_row_keys(df)


# =========================================================
# Toolbar
# =========================================================

st.subheader("Customers")

col1, col2, col3 = st.columns([1, 1, 3])

with col1:

    if st.button("➕ Add Row"):

        new_row = pd.DataFrame(
            [{
                "ID": None,
                "NAME": "",
                "EMAIL": "",
                "STATUS": "",
                "_row_key": str(uuid.uuid4()),
            }]
        )

        st.session_state.customers_df = pd.concat(
            [
                st.session_state.customers_df,
                new_row,
            ],
            ignore_index=True,
        )

        st.rerun()


with col2:

    rows_to_add = st.number_input(
        "Rows for paste",
        min_value=1,
        max_value=1000,
        value=10,
        step=1,
    )


with col3:

    if st.button("📋 Add Blank Rows for Paste"):

        blank_rows = pd.DataFrame(
            [
                {
                    "ID": None,
                    "NAME": "",
                    "EMAIL": "",
                    "STATUS": "",
                    "_row_key": str(uuid.uuid4()),
                }
                for _ in range(rows_to_add)
            ]
        )

        st.session_state.customers_df = pd.concat(
            [
                st.session_state.customers_df,
                blank_rows,
            ],
            ignore_index=True,
        )

        st.rerun()


st.info(
    "Tip: To paste new records from Excel, add blank rows first, "
    "click the first blank ID cell, then use Ctrl+V."
)


# =========================================================
# Build AG Grid
# =========================================================

df = st.session_state.customers_df.copy()

gb = GridOptionsBuilder.from_dataframe(df)

# Default behavior

gb.configure_default_column(
    editable=True,
    resizable=True,
    sortable=True,
    filter=True,
)

# ID

gb.configure_column(
    "ID",
    editable=True,
    type=["numericColumn"],
)

# Name

gb.configure_column(
    "NAME",
    editable=True,
)

# Email

gb.configure_column(
    "EMAIL",
    editable=True,
)

# Status

gb.configure_column(
    "STATUS",
    editable=True,
)

# Internal row key
# Hidden from the user

gb.configure_column(
    "_row_key",
    hide=True,
    editable=False,
)

# Selection

gb.configure_selection(
    selection_mode="multiple",
    use_checkbox=True,
)

# Clipboard / Excel-like behavior

gb.configure_grid_options(
    enableRangeSelection=True,
    enableClipboard=True,
    suppressClipboardPaste=False,
)

grid_options = gb.build()


# =========================================================
# Display AG Grid
# =========================================================

response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED
        | GridUpdateMode.SELECTION_CHANGED,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    height=550,
    theme="streamlit",
    key="customers_grid",
)


# =========================================================
# Capture edited data
# =========================================================

edited_df = response["data"]

edited_df = pd.DataFrame(edited_df)

st.session_state.customers_df = edited_df


# =========================================================
# Delete selected rows
# =========================================================

selected_rows = response.get("selected_rows", [])

if selected_rows is not None:

    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict("records")

    if len(selected_rows) > 0:

        st.write(
            f"**{len(selected_rows)} row(s) selected**"
        )

        if st.button("🗑️ Delete Selected Rows"):

            selected_keys = {
                row["_row_key"]
                for row in selected_rows
                if "_row_key" in row
            }

            st.session_state.customers_df = (
                st.session_state.customers_df[
                    ~st.session_state.customers_df["_row_key"].isin(
                        selected_keys
                    )
                ]
                .reset_index(drop=True)
            )

            st.rerun()


# =========================================================
# Temporary Save button
# =========================================================

st.divider()

col1, col2 = st.columns([1, 1])

with col1:

    if st.button(
        "💾 Save Changes",
        type="primary",
    ):

        st.warning(
            "Save to Snowflake is not implemented yet. "
            "Your changes currently exist only in this Streamlit session."
        )


with col2:

    if st.button("↩️ Reload from Snowflake"):

        st.session_state.customers_df = add_row_keys(
            load_customers()
        )

        st.rerun()


# =========================================================
# Debug / preview
# =========================================================

with st.expander("Preview current data"):

    preview_df = st.session_state.customers_df.drop(
        columns=["_row_key"],
        errors="ignore",
    )

    st.dataframe(
        preview_df,
        use_container_width=True,
    )
