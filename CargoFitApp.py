# OnFly Air Cargo Fit Tool - Advanced Version with Searchable Dropdowns and Multiple Parts
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------
# CONFIGURATION
# ---------------------------
st.set_page_config(page_title="OnFly Air Cargo Fit Tool", layout="centered")
st.image("OFA_Gold_Black.png", width=200)
st.title("OnFly Air Cargo Fit Tool")
st.markdown("Determine if cargo and mechanics fit into the selected aircraft based on dimensions and weight.")

# ---------------------------
# LOAD DATA
# ---------------------------
aircraft_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?output=csv"
parts_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?gid=1047329111&single=true&output=csv"
spreadsheet_id = "1JkU0-4mkXkYkRQ6-7ep1tkXUjkJrQsMZ0Tsp5rFCIkk"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    return df

@st.cache_data
def clean_aircraft(df):
    numeric = df.columns.drop("Aircraft", errors="ignore")
    for col in numeric:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("~", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df_aircraft = clean_aircraft(load_data(aircraft_url))
df_parts = load_data(parts_url)

# ---------------------------
# STEP 1: SELECT AIRCRAFT
# ---------------------------
st.header("Step 1: Select an Aircraft")
selected_aircraft = st.selectbox("Choose Aircraft", df_aircraft["Aircraft"].dropna().unique(), index=0)
aircraft_data = df_aircraft[df_aircraft["Aircraft"] == selected_aircraft].iloc[0]

st.subheader("Selected Aircraft Specs")
st.write(f"Door: {aircraft_data['Door Width (in)']}\" W x {aircraft_data['Door Height (in)']}\" H")
st.write(f"Cabin: {aircraft_data['Cabin Length (in)']}\" L x {aircraft_data['Cabin Width (in)']}\" W x {aircraft_data['Cabin Height (in)']}\" H")
st.write(f"Max Payload: {aircraft_data['Max Payload (lbs)']} lbs")

st.markdown("---")

# ---------------------------
# STEP 2: ENTER MULTIPLE PARTS
# ---------------------------
st.header("Step 2: Add Cargo (Part) Details")

if "parts_list" not in st.session_state:
    st.session_state.parts_list = []

with st.form("add_part_form"):
    part_names = df_parts["Part"].dropna().astype(str).unique().tolist()
    part_name = st.selectbox("Choose Existing Part or Enter New Name", ["(New)"] + sorted(part_names))

    if part_name == "(New)":
        part_name = st.text_input("New Part Name", value="")
        length = st.number_input("Length (in)", min_value=0.0, step=0.1)
        width = st.number_input("Width (in)", min_value=0.0, step=0.1)
        height = st.number_input("Height (in)", min_value=0.0, step=0.1)
        weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1)
    else:
        match = df_parts[df_parts["Part"] == part_name]
        if not match.empty:
            record = match.iloc[0]
            part_name = record["Part"]
            length, width, height, weight = record[["Length (in)", "Width (in)", "Height (in)", "Weight (lbs.)"]]

    rotate = st.checkbox("Rotate part for door/cabin check? (swap L/W)")
    if rotate:
        length, width = width, length

    submitted = st.form_submit_button("Add Part")
    if submitted:
        new_part = {
            "Name": part_name,
            "Length": length,
            "Width": width,
            "Height": height,
            "Weight": weight
        }
        st.session_state.parts_list.append(new_part)

        try:
            sheet = client.open_by_key(spreadsheet_id).worksheet("Historical Parts")
            sheet.append_row([part_name, length, width, height, weight])
            st.success("Part saved to Google Sheet")
        except Exception as e:
            st.warning(f"Could not write to Google Sheet: {e}")

if st.session_state.parts_list:
    st.subheader("Selected Parts")
    st.table(pd.DataFrame(st.session_state.parts_list))

st.markdown("---")

# (Rest of the app continues unchanged ...)
# Including Steps 3–5

