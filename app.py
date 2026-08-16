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
# PAGE
# =========================================================

st.set_page_config(
    page_title="Data Editor",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Customer Data")


# =========================================================
# SNOWFLAKE CONNECTION
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
# LOAD DATA
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
# INTERNAL ROW KEY
# =========================================================

def add_row_keys(df):

    df = df.copy()

    df["_row_key"] = [
        str(uuid.uuid4())
        for _ in range(len(df))
    ]

    return df


# =========================================================
# SESSION STATE
# =========================================================

if "data" not in st.session_state:

    st.session_state.data = add_row_keys(
        load_customers()
    )


if "grid_version" not in st.session_state:

    st.session_state.grid_version = 0


# =========================================================
# TOOLBAR
# =========================================================

col1, col2, col3 = st.columns([1, 1, 6])


# ---------------------------------------------------------
# ADD ROW
# ---------------------------------------------------------

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

        st.session_state.data = pd.concat(
            [
                st.session_state.data,
                new_row,
            ],
            ignore_index=True,
        )

        st.session_state.grid_version += 1

        st.rerun()


# ---------------------------------------------------------
# DELETE SELECTED
# ---------------------------------------------------------

with col2:

    delete_clicked = st.button(
        "🗑️ Delete Selected"
    )


# =========================================================
# GRID
# =========================================================

df = st.session_state.data.copy()


gb = GridOptionsBuilder.from_dataframe(df)


# Default column behavior

gb.configure_default_column(
    editable=True,
    resizable=True,
    sortable=True,
    filter=True,
)


# ID

gb.configure_column(
    "ID",
    header_name="ID",
    editable=True,
)


# NAME

gb.configure_column(
    "NAME",
    header_name="NAME",
    editable=True,
)


# EMAIL

gb.configure_column(
    "EMAIL",
    header_name="EMAIL",
    editable=True,
)


# STATUS

gb.configure_column(
    "STATUS",
    header_name="STATUS",
    editable=True,
)


# Internal key — never show to user

gb.configure_column(
    "_row_key",
    hide=True,
    editable=False,
)


# Row selection

gb.configure_selection(
    selection_mode="multiple",
    use_checkbox=True,
)


# Excel-like clipboard behavior

gb.configure_grid_options(
    enableRangeSelection=True,
    enableClipboard=True,
    suppressClipboardPaste=False,
)


grid_options = gb.build()


# =========================================================
# RENDER GRID
# =========================================================

response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=(
        GridUpdateMode.VALUE_CHANGED
        | GridUpdateMode.SELECTION_CHANGED
    ),
    fit_columns_on_grid_load=True,
    height=600,
    theme="streamlit",
    allow_unsafe_jscode=True,
    key=f"customer_grid_{st.session_state.grid_version}",
)


# =========================================================
# CAPTURE CHANGES
# =========================================================

if response.get("data") is not None:

    edited_data = pd.DataFrame(
        response["data"]
    )

    st.session_state.data = edited_data


# =========================================================
# DELETE SELECTED
# =========================================================

if delete_clicked:

    selected_rows = response.get(
        "selected_rows",
        []
    )

    if isinstance(
        selected_rows,
        pd.DataFrame
    ):

        selected_rows = selected_rows.to_dict(
            "records"
        )

    if selected_rows:

        selected_keys = {
            row["_row_key"]
            for row in selected_rows
            if "_row_key" in row
        }

        st.session_state.data = (
            st.session_state.data[
                ~st.session_state.data[
                    "_row_key"
                ].isin(selected_keys)
            ]
            .reset_index(drop=True)
        )

        st.session_state.grid_version += 1

        st.rerun()


# =========================================================
# SAVE / DISCARD
# =========================================================

st.divider()

col1, col2 = st.columns([1, 1])


with col1:

    if st.button(
        "💾 Save Changes",
        type="primary",
    ):

        st.info(
            "Snowflake save logic will be added next."
        )


with col2:

    if st.button(
        "↩️ Discard Changes"
    ):

        st.session_state.data = add_row_keys(
            load_customers()
        )

        st.session_state.grid_version += 1

        st.rerun()
