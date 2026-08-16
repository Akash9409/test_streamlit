import streamlit as st
import snowflake.connector
import pandas as pd
import io


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Snowflake Data Editor",
    page_icon="📊",
    layout="wide",
)


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


DATABASE = "STREAMLIT_EXCEL_APP"
SCHEMA = "DATA"


# =========================================================
# GET TABLES
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
# GET COLUMNS
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
# LOAD TABLE
# =========================================================

def load_table(table_name, columns):

    quoted_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    query = f'''
        SELECT {quoted_columns}
        FROM "{DATABASE}"."{SCHEMA}"."{table_name}"
    '''

    conn = get_connection()

    return pd.read_sql(query, conn)


# =========================================================
# SAVE TABLE
# =========================================================

def save_table(table_name, df, column_metadata):

    conn = get_connection()

    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # Start transaction
        # -------------------------------------------------

        cursor.execute("BEGIN")

        # -------------------------------------------------
        # Remove existing records
        # -------------------------------------------------

        cursor.execute(
            f'''
            DELETE FROM "{DATABASE}"."{SCHEMA}"."{table_name}"
            '''
        )

        # -------------------------------------------------
        # Insert current grid contents
        # -------------------------------------------------

        if not df.empty:

            columns = column_metadata[
                "COLUMN_NAME"
            ].tolist()

            quoted_columns = ", ".join(
                f'"{column}"'
                for column in columns
            )

            placeholders = ", ".join(
                ["%s"] * len(columns)
            )

            insert_query = f'''
                INSERT INTO "{DATABASE}"."{SCHEMA}"."{table_name}"
                ({quoted_columns})
                VALUES ({placeholders})
            '''

            # Convert pandas NaN / NaT to None
            # so Snowflake receives NULL.

            insert_df = df.copy()

            insert_df = insert_df.where(
                pd.notnull(insert_df),
                None
            )

            records = [
                tuple(row)
                for row in insert_df.itertuples(
                    index=False,
                    name=None
                )
            ]

            cursor.executemany(
                insert_query,
                records
            )

        # -------------------------------------------------
        # Commit
        # -------------------------------------------------

        cursor.execute("COMMIT")

    except Exception:

        cursor.execute("ROLLBACK")

        raise

    finally:

        cursor.close()


# =========================================================
# COLUMN CONFIG
# =========================================================

def build_column_config(column_metadata):

    config = {}

    for _, row in column_metadata.iterrows():

        column_name = row["COLUMN_NAME"]
        data_type = row["DATA_TYPE"]

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

            config[column_name] = (
                st.column_config.NumberColumn(
                    column_name
                )
            )

        elif data_type == "DATE":

            config[column_name] = (
                st.column_config.DateColumn(
                    column_name
                )
            )

        elif "TIMESTAMP" in data_type:

            config[column_name] = (
                st.column_config.DatetimeColumn(
                    column_name
                )
            )

        elif data_type == "BOOLEAN":

            config[column_name] = (
                st.column_config.CheckboxColumn(
                    column_name
                )
            )

        else:

            config[column_name] = (
                st.column_config.TextColumn(
                    column_name
                )
            )

    return config


# =========================================================
# PARSE EXCEL PASTE
# =========================================================

def parse_excel_paste(text, columns):

    if not text or not text.strip():

        return None, "Nothing was pasted."

    try:

        pasted_df = pd.read_csv(
            io.StringIO(text),
            sep="\t",
            header=None,
            dtype=str,
            keep_default_na=False,
        )

    except Exception as e:

        return None, f"Could not read pasted data: {e}"

    # Remove empty rows

    pasted_df = pasted_df[
        pasted_df.apply(
            lambda row: any(
                str(value).strip() != ""
                for value in row
            ),
            axis=1,
        )
    ].reset_index(drop=True)

    if pasted_df.empty:

        return None, "No data was found."

    # Detect header

    first_row = [
        str(value).strip().upper()
        for value in pasted_df.iloc[0].tolist()
    ]

    expected_columns = [
        str(column).strip().upper()
        for column in columns
    ]

    has_header = (
        len(first_row) == len(expected_columns)
        and first_row == expected_columns
    )

    if has_header:

        pasted_df = pasted_df.iloc[1:].reset_index(
            drop=True
        )

    # Validate column count

    if pasted_df.shape[1] != len(columns):

        return (
            None,
            (
                f"Expected {len(columns)} columns "
                f"but received {pasted_df.shape[1]}."
            ),
        )

    pasted_df.columns = columns

    return pasted_df, None


# =========================================================
# SESSION STATE
# =========================================================

if "selected_table" not in st.session_state:

    st.session_state.selected_table = None

if "table_data" not in st.session_state:

    st.session_state.table_data = None

if "editor_version" not in st.session_state:

    st.session_state.editor_version = 0

if "show_paste_dialog" not in st.session_state:

    st.session_state.show_paste_dialog = False


# =========================================================
# HEADER
# =========================================================

st.title("📊 Snowflake Data Editor")


# =========================================================
# TABLES
# =========================================================

tables = get_tables()

if not tables:

    st.error(
        f"No tables found in {DATABASE}.{SCHEMA}."
    )

    st.stop()


# =========================================================
# TABLE SELECTOR
# =========================================================

selected_table = st.selectbox(
    "Select table",
    tables,
)


# =========================================================
# TABLE CHANGE
# =========================================================

if (
    st.session_state.selected_table
    != selected_table
):

    st.session_state.selected_table = selected_table

    column_metadata = get_columns(
        selected_table
    )

    columns = column_metadata[
        "COLUMN_NAME"
    ].tolist()

    st.session_state.table_data = load_table(
        selected_table,
        columns,
    )

    st.session_state.editor_version += 1


# =========================================================
# COLUMN METADATA
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
# INITIAL DATA
# =========================================================

if st.session_state.table_data is None:

    st.session_state.table_data = load_table(
        selected_table,
        columns,
    )


# =========================================================
# DATA EDITOR
# =========================================================

edited_df = st.data_editor(

    st.session_state.table_data,

    key=(
        f"editor_"
        f"{selected_table}_"
        f"{st.session_state.editor_version}"
    ),

    num_rows="dynamic",

    hide_index=True,

    width="stretch",

    height=600,

    column_config=build_column_config(
        column_metadata
    ),
)


# =========================================================
# ACTION BUTTONS
# =========================================================

st.divider()

col1, col2, col3 = st.columns(
    [1, 1, 1]
)


# =========================================================
# PASTE
# =========================================================

with col1:

    if st.button(
        "📋 Paste from Excel"
    ):

        st.session_state.show_paste_dialog = True


# =========================================================
# SAVE
# =========================================================

with col2:

    if st.button(
        "💾 Save Changes",
        type="primary",
    ):

        try:

            with st.spinner(
                "Saving changes to Snowflake..."
            ):

                save_table(
                    selected_table,
                    edited_df,
                    column_metadata,
                )

            # Update local state to exactly what
            # was saved.

            st.session_state.table_data = (
                edited_df.copy()
            )

            # Clear cached table metadata/data if necessary.

            st.success(
                f"{selected_table} saved successfully."
            )

        except Exception as e:

            st.error(
                f"Failed to save changes: {e}"
            )


# =========================================================
# DISCARD
# =========================================================

with col3:

    if st.button(
        "↩️ Discard Changes"
    ):

        with st.spinner(
            "Reloading from Snowflake..."
        ):

            st.session_state.table_data = (
                load_table(
                    selected_table,
                    columns,
                )
            )

        st.session_state.editor_version += 1

        st.success(
            "Changes discarded."
        )

        st.rerun()


# =========================================================
# PASTE DIALOG
# =========================================================

if st.session_state.show_paste_dialog:

    @st.dialog("Paste from Excel")
    def paste_dialog():

        st.write(
            "Copy rows from Excel and paste them below."
        )

        st.caption(
            "Multiple rows and columns are supported. "
            "Column headers are detected automatically."
        )

        pasted_text = st.text_area(
            "Excel data",
            height=250,
            placeholder=(
                "Copy cells from Excel and press "
                "Ctrl + V here..."
            ),
        )

        button_col1, button_col2 = st.columns(
            [1, 1]
        )

        with button_col1:

            if st.button(
                "Add Rows",
                type="primary",
            ):

                new_rows, error = parse_excel_paste(
                    pasted_text,
                    columns,
                )

                if error:

                    st.error(error)

                else:

                    combined_df = pd.concat(
                        [
                            edited_df,
                            new_rows,
                        ],
                        ignore_index=True,
                    )

                    st.session_state.table_data = (
                        combined_df
                    )

                    st.session_state.editor_version += 1

                    st.session_state.show_paste_dialog = (
                        False
                    )

                    st.rerun()

        with button_col2:

            if st.button("Cancel"):

                st.session_state.show_paste_dialog = (
                    False
                )

                st.rerun()

    paste_dialog()
