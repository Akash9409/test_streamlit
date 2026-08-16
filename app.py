import streamlit as st
import snowflake.connector
import pandas as pd


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Snowflake Data Editor",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# CONNECTION
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
# CONSTANTS
# =========================================================

DATABASE = "STREAMLIT_EXCEL_APP"
SCHEMA = "DATA"


# =========================================================
# GET AVAILABLE TABLES
# =========================================================

@st.cache_data(ttl=60)
def get_tables():

    conn = get_connection()

    query = f"""
        SELECT TABLE_NAME
        FROM {DATABASE}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{SCHEMA}'
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """

    df = pd.read_sql(query, conn)

    return df["TABLE_NAME"].tolist()


# =========================================================
# GET COLUMNS FOR A TABLE
# =========================================================

@st.cache_data(ttl=60)
def get_columns(table_name):

    conn = get_connection()

    query = f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            ORDINAL_POSITION
        FROM {DATABASE}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{SCHEMA}'
          AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
    """

    return pd.read_sql(query, conn)


# =========================================================
# LOAD TABLE DATA
# =========================================================

def load_table(table_name, columns):

    # Column names come directly from Snowflake metadata.
    # We quote them to safely handle names containing
    # special characters or reserved words.

    quoted_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    query = f"""
        SELECT {quoted_columns}
        FROM "{DATABASE}"."{SCHEMA}"."{table_name}"
    """

    conn = get_connection()

    return pd.read_sql(query, conn)


# =========================================================
# HEADER
# =========================================================

st.title("📊 Snowflake Data Editor")


# =========================================================
# FIND TABLES
# =========================================================

tables = get_tables()


if not tables:

    st.error(
        f"No tables found in {DATABASE}.{SCHEMA}."
    )

    st.stop()


# =========================================================
# TABLE DROPDOWN
# =========================================================

selected_table = st.selectbox(
    "Select table",
    tables,
)


# =========================================================
# GET COLUMN METADATA
# =========================================================

column_metadata = get_columns(
    selected_table
)

columns = column_metadata[
    "COLUMN_NAME"
].tolist()


if not columns:

    st.error(
        f"No columns found for {selected_table}."
    )

    st.stop()


# =========================================================
# SESSION STATE
# =========================================================

table_key = f"table_data_{selected_table}"

editor_key = f"editor_{selected_table}"


if table_key not in st.session_state:

    st.session_state[table_key] = load_table(
        selected_table,
        columns,
    )


# =========================================================
# CURRENT DATA
# =========================================================

df = st.session_state[table_key]


# =========================================================
# DYNAMIC COLUMN CONFIG
# =========================================================

column_config = {}

for _, row in column_metadata.iterrows():

    column_name = row["COLUMN_NAME"]
    data_type = row["DATA_TYPE"]

    # Numeric Snowflake types

    if data_type in (
        "NUMBER",
        "DECIMAL",
        "NUMERIC",
        "INTEGER",
        "INT",
        "BIGINT",
        "SMALLINT",
        "FLOAT",
        "FLOAT4",
        "FLOAT8",
        "DOUBLE",
        "REAL",
    ):

        column_config[column_name] = (
            st.column_config.NumberColumn(
                column_name,
            )
        )

    # Date

    elif data_type == "DATE":

        column_config[column_name] = (
            st.column_config.DateColumn(
                column_name,
            )
        )

    # Timestamp

    elif "TIMESTAMP" in data_type:

        column_config[column_name] = (
            st.column_config.DatetimeColumn(
                column_name,
            )
        )

    # Boolean

    elif data_type == "BOOLEAN":

        column_config[column_name] = (
            st.column_config.CheckboxColumn(
                column_name,
            )
        )

    # Everything else

    else:

        column_config[column_name] = (
            st.column_config.TextColumn(
                column_name,
            )
        )


# =========================================================
# DATA EDITOR
# =========================================================

edited_df = st.data_editor(

    df,

    key=editor_key,

    num_rows="dynamic",

    hide_index=True,

    width="stretch",

    height=600,

    column_config=column_config,
)


# =========================================================
# STORE CURRENT EDITS
# =========================================================

st.session_state[table_key] = edited_df


# =========================================================
# ACTIONS
# =========================================================

st.divider()

col1, col2 = st.columns([1, 1])


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

with col1:

    if st.button(
        "💾 Save Changes",
        type="primary",
    ):

        st.info(
            "Snowflake save logic will be implemented next."
        )


# ---------------------------------------------------------
# DISCARD
# ---------------------------------------------------------

with col2:

    if st.button("↩️ Discard Changes"):

        st.session_state[table_key] = load_table(
            selected_table,
            columns,
        )

        # Remove the editor state so the widget
        # is recreated using the fresh Snowflake data.

        if editor_key in st.session_state:

            del st.session_state[editor_key]

        st.rerun()
