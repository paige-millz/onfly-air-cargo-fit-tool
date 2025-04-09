import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# CONFIGURATION
# ---------------------------
st.set_page_config(page_title="OnFly Air Cargo Fit Tool", layout="centered")
st.image("OFA_Gold_Black.png", width=200)
st.title("OnFly Air Cargo Fit Tool")
st.markdown("This app determines if a specified piece of cargo fits into the selected aircraft based on dimensions and payload limits.")

# ---------------------------
# LOAD DATA
# ---------------------------
aircraft_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?output=csv"
parts_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?gid=1047329111&single=true&output=csv"

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
aircraft_list = df_aircraft["Aircraft"].dropna().unique()
aircraft = st.selectbox("Choose Aircraft", aircraft_list)
aircraft_data = df_aircraft[df_aircraft["Aircraft"] == aircraft].iloc[0]

st.subheader("Selected Aircraft Details")
st.write(f"**Door:** {aircraft_data['Door Width (in)']}\" W x {aircraft_data['Door Height (in)']}\" H")
st.write(f"**Cabin:** {aircraft_data['Cabin Length (in)']}\" L x {aircraft_data['Cabin Width (in)']}\" W x {aircraft_data['Cabin Height (in)']}\" H")
st.write(f"**Payload:** {aircraft_data['Max Payload (lbs)']} lbs")
st.write(f"**Seats:** {int(aircraft_data['Number of Seats'])} (Removable: {int(aircraft_data['Removable Seats'])})")
st.write(f"**Seat Info:** {aircraft_data['Seat Weight (lbs)']} lbs | {aircraft_data['Seat Length (in)']} x {aircraft_data['Seat Width (in)']} x {aircraft_data['Seat Height (in)']} in")

st.markdown("---")

# ---------------------------
# STEP 2: ENTER CARGO / PART
# ---------------------------
st.header("Step 2: Enter Cargo (Part) Details")

part_names = df_parts["Part Name"].dropna().unique().tolist() if "Part Name" in df_parts else []
selected_part = st.selectbox("Select a Historical Part", ["(None)"] + sorted(part_names))

if selected_part != "(None)":
    match = df_parts[df_parts["Part Name"] == selected_part].iloc[0]
    part_name = selected_part
    part_length = match["Length (in)"]
    part_width = match["Width (in)"]
    part_height = match["Height (in)"]
    part_weight = match["Weight (lbs)"]
    st.success(f"Loaded: {part_name}")
else:
    part_name = st.text_input("Part Name")
    col1, col2, col3 = st.columns(3)
    with col1:
        part_length = st.number_input("Length (in)", min_value=0.0, step=0.1)
    with col2:
        part_width = st.number_input("Width (in)", min_value=0.0, step=0.1)
    with col3:
        part_height = st.number_input("Height (in)", min_value=0.0, step=0.1)
    part_weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1)

st.markdown("---")

# ---------------------------
# STEP 3: SAVE/LOAD PARTS
# ---------------------------
st.header("Step 3: Save/Load Parts")
if "saved_parts" not in st.session_state:
    st.session_state.saved_parts = {}

if st.button("Save Part"):
    st.session_state.saved_parts[part_name] = {
        "Length": part_length,
        "Width": part_width,
        "Height": part_height,
        "Weight": part_weight
    }
    st.success(f"Saved part: {part_name}")

if st.session_state.saved_parts:
    saved_selected = st.selectbox("Load a saved part", ["(None)"] + list(st.session_state.saved_parts.keys()))
    if saved_selected != "(None)" and st.button("Load Saved Part"):
        loaded = st.session_state.saved_parts[saved_selected]
        part_length = loaded["Length"]
        part_width = loaded["Width"]
        part_height = loaded["Height"]
        part_weight = loaded["Weight"]
        st.info(f"Loaded part: {saved_selected}")

st.markdown("---")

# ---------------------------
# STEP 4: MISSION FEASIBILITY
# ---------------------------
st.header("Step 4: Mission Feasibility Calculation")

door_w = aircraft_data["Door Width (in)"]
door_h = aircraft_data["Door Height (in)"]
cabin_l = aircraft_data["Cabin Length (in)"]
cabin_w = aircraft_data["Cabin Width (in)"]
cabin_h = aircraft_data["Cabin Height (in)"]
max_payload = aircraft_data["Max Payload (lbs)"]

mechanics = st.checkbox("Are mechanics traveling?")
mech_count = st.number_input("Mechanics", min_value=0, value=1) if mechanics else 0
tool_weight = st.number_input("Tool Weight (lbs)", min_value=0.0) if mechanics else 0.0

remove_seat = st.checkbox("Remove a seat (cargo-only flight)?")
seat_weight = aircraft_data["Seat Weight (lbs)"] if remove_seat else 0

# Fit checks
fits_door = (part_length <= door_w and part_width <= door_h) or (part_length <= door_h and part_width <= door_w)
fits_cabin = part_length <= cabin_l and part_width <= cabin_w and part_height <= cabin_h
total_payload = part_weight + (mech_count * 180) + tool_weight
available_payload = max_payload + seat_weight

# Output
st.write(f"**Total Required Payload:** {total_payload:.2f} lbs")
st.write(f"**Available Payload:** {available_payload:.2f} lbs")
st.success("✅ Payload check: Within limits!" if total_payload <= available_payload else "❌ Payload check: Overweight!")
st.success("✅ Door fit check: Pass" if fits_door else "❌ Door fit check: FAIL")
st.success("✅ Cabin fit check: Pass" if fits_cabin else "❌ Cabin fit check: FAIL")

st.markdown("---")

# ---------------------------
# STEP 5: VISUALIZATION
# ---------------------------
st.header("Step 5: Visualization")
fig, ax = plt.subplots(figsize=(6, 6))
door_rect = plt.Rectangle((0, 0), door_w, door_h, edgecolor='blue', fill=False, lw=2, label='Door')
cargo_rect = plt.Rectangle((0, 0), part_length, part_width, edgecolor='green' if fits_door else 'red', fill=False, lw=2, label='Cargo')
ax.add_patch(door_rect)
ax.add_patch(cargo_rect)
ax.set_xlim(0, max(door_w, part_length) + 10)
ax.set_ylim(0, max(door_h, part_width) + 10)
ax.set_aspect('equal')
ax.set_xlabel("inches")
ax.set_ylabel("inches")
ax.set_title("Door vs. Cargo Fit")
ax.legend()
st.pyplot(fig)

st.markdown("The visual above compares your cargo against the door. Green = fits. Red = does not fit.")
