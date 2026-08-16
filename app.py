import streamlit as st
import snowflake.connector

st.set_page_config(
    page_title="Snowflake Data Editor",
    page_icon="📊",
    layout="wide",
)

st.title("Snowflake Data Editor")

try:
    conn = snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )

    st.success("Connected to Snowflake!")

    cursor = conn.cursor()

    # Show current Snowflake context
    cursor.execute("""
        SELECT
            CURRENT_DATABASE(),
            CURRENT_SCHEMA(),
            CURRENT_ROLE(),
            CURRENT_WAREHOUSE()
    """)

    context = cursor.fetchone()

    st.write("### Snowflake connection details")

    st.write({
        "Database": context[0],
        "Schema": context[1],
        "Role": context[2],
        "Warehouse": context[3],
    })

    # Check how many records exist
    cursor.execute("""
        SELECT COUNT(*)
        FROM STREAMLIT_EXCEL_APP.DATA.CUSTOMERS
    """)

    count = cursor.fetchone()[0]

    st.write(f"### Customers rows found: {count}")

    # Display data
    cursor.execute("""
        SELECT *
        FROM STREAMLIT_EXCEL_APP.DATA.CUSTOMERS
        ORDER BY ID
    """)

    rows = cursor.fetchall()

    columns = [column[0] for column in cursor.description]

    st.dataframe(
        rows,
        column_config={
            column: st.column_config.TextColumn(column)
            for column in columns
        },
        use_container_width=True,
    )

    cursor.close()
    conn.close()

except Exception as e:
    st.error("Could not connect to Snowflake.")
    st.exception(e)
