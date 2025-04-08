import streamlit as st
import pandas as pd
import math

st.title("OnFly Air Cargo Fit Tool")
st.markdown("This app determines if a specified piece of cargo fits into the selected aircraft based on dimensions and payload limits.")

# URL to the published Google Sheet CSV
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?output=csv"

@st.cache_data
def load_aircraft_data(url):
    try:
        df = pd.read_csv(url)
        # Clean any leading/trailing whitespace from all column names
        df.columns = [col.strip() for col in df.columns]
        
        # Convert dimension and weight columns to numeric, coerce errors to NaN
        numeric_columns = [
            "Door Width (in)", "Door Height (in)",
            "Cabin Length (in)", "Cabin Width (in)", "Cabin Height (in)",
            "Max Payload (lbs)", "Number of Seats", "Removable Seats",
            "Seat Weight (lbs)", "Seat Length (in)", "Seat Width (in)", "Seat Height (in)"
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df
    except Exception as e:
        st.error(f"Error loading aircraft data: {e}")
        return pd.DataFrame()

# Load aircraft specs from the Google Sheet
df_aircraft = load_aircraft_data(csv_url)

if df_aircraft.empty:
    st.error("Aircraft data could not be loaded. Please check your network connection or the spreadsheet settings.")
else:
    # Debug: Show available columns
    st.write("Available columns:", df_aircraft.columns.tolist())

    st.sidebar.subheader("Aircraft Selection")
    # Replace "Model" with "Aircraft" if that's your actual column name
    aircraft_options = df_aircraft["Aircraft"].dropna().unique()
    selected_aircraft_model = st.sidebar.selectbox("Select Aircraft", options=aircraft_options)
    
    # Get the row for the selected aircraft
    selected_aircraft = df_aircraft[df_aircraft["Aircraft"] == selected_aircraft_model].iloc[0]
    
    st.subheader("Selected Aircraft Details")
    st.write(f"**Aircraft:** {selected_aircraft['Aircraft']}")
    st.write(f"**Cargo Door Dimensions:** {selected_aircraft['Door Width (in)']} in (W) x {selected_aircraft['Door Height (in)']} in (H)")
    st.write(f"**Cabin Dimensions:** {selected_aircraft['Cabin Length (in)']} in (L) x {selected_aircraft['Cabin Width (in)']} in (W) x {selected_aircraft['Cabin Height (in)']} in (H)")
    st.write(f"**Max Payload:** {selected_aircraft['Max Payload (lbs)']} lbs")
    st.write(f"**Seats:** {selected_aircraft['Number of Seats']} (Removable: {selected_aircraft['Removable Seats']})")
    st.write(f"**Seat Info:** Weight: {selected_aircraft['Seat Weight (lbs)']} lbs, Dimensions: "
             f"{selected_aircraft['Seat Length (in)']} x {selected_aircraft['Seat Width (in)']} x "
             f"{selected_aircraft['Seat Height (in)']} in")
    
    st.markdown("---")
    
    # Cargo (Part) Input
    st.subheader("Cargo (Part) Input")
    part_name = st.text_input("Part Name")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        part_length = st.number_input("Length (in)", min_value=0.0, value=0.0, step=0.1)
    with col2:
        part_width = st.number_input("Width (in)", min_value=0.0, value=0.0, step=0.1)
    with col3:
        part_height = st.number_input("Height (in)", min_value=0.0, value=0.0, step=0.1)
        
    part_weight = st.number_input("Weight (lbs)", min_value=0.0, value=0.0, step=1.0)
    
    # Mechanics Input
    mechanics_travel = st.checkbox("Are mechanics traveling?")
    if mechanics_travel:
        num_mechanics = st.number_input("Number of Mechanics", min_value=1, value=1, step=1)
        avg_mech_weight = st.number_input("Average Weight per Mechanic (lbs)", min_value=0.0, value=180.0, step=1.0)
        tool_weight = st.number_input("Total Tool Weight (lbs)", min_value=0.0, value=0.0, step=1.0)
    else:
        num_mechanics = 0
        avg_mech_weight = 0.0
        tool_weight = 0.0
    
    # Seat Removal Option
    remove_seat = st.checkbox("Remove a seat (cargo-only flight)?")
    if remove_seat:
        max_removable = selected_aircraft.get("Removable Seats", 0)
        # Convert to int if not NaN
        if pd.notnull(max_removable):
            max_removable = int(max_removable)
        else:
            max_removable = 0
        seats_removed = st.number_input("Number of Seats to Remove",
                                        min_value=1,
                                        max_value=max_removable if max_removable else 1,
                                        value=1,
                                        step=1)
    else:
        seats_removed = 0
    
    st.markdown("---")
    
    # Saved Parts
    st.subheader("Saved Parts")
    if "saved_parts" not in st.session_state:
        st.session_state.saved_parts = {}
        
    if st.button("Save Part"):
        if part_name:
            st.session_state.saved_parts[part_name] = {
                "Length": part_length,
                "Width": part_width,
                "Height": part_height,
                "Weight": part_weight
            }
            st.success(f"Saved part: {part_name}")
        else:
            st.error("Please provide a Part Name to save.")

    if st.session_state.saved_parts:
        saved_options = list(st.session_state.saved_parts.keys())
        saved_selected = st.selectbox("Select a saved part to load values", options=saved_options)
        if st.button("Load Selected Saved Part"):
            loaded = st.session_state.saved_parts[saved_selected]
            part_length = loaded["Length"]
            part_width = loaded["Width"]
            part_height = loaded["Height"]
            part_weight = loaded["Weight"]
            st.info(f"Loaded part: {saved_selected}")
    
    st.markdown("---")
    
    # ========================
    # Calculation and Fit Checks
    # ========================
    st.subheader("Calculation Results")
    
    # Total required payload weight includes cargo, mechanics, and tools
    total_cargo_weight = part_weight + (num_mechanics * avg_mech_weight) + tool_weight
    
    # If seats are removed, add the weight back to available payload capacity.
    seat_weight_col = selected_aircraft.get("Seat Weight (lbs)", float('nan'))
    if seats_removed > 0 and pd.notnull(seat_weight_col):
        additional_payload = seats_removed * seat_weight_col
    else:
        additional_payload = 0

    max_payload_col = selected_aircraft["Max Payload (lbs)"]
    if pd.isnull(max_payload_col):
        st.warning("Max payload data is missing for this aircraft. Payload check not possible.")
        available_payload = float('nan')
    else:
        available_payload = max_payload_col + additional_payload
    
    st.write(f"**Total Required Payload Weight:** {total_cargo_weight:.2f} lbs")
    if pd.notnull(available_payload):
        st.write(f"**Available Payload:** {available_payload:.2f} lbs")
        if total_cargo_weight <= available_payload:
            st.success("Payload check: Within available limits!")
        else:
            st.error("Payload check: Over weight!")
    else:
        st.write("**Available Payload:** Unknown")
    
    # Door Fit Check
    door_w = selected_aircraft["Door Width (in)"]
    door_h = selected_aircraft["Door Height (in)"]
    
    if pd.isnull(door_w) or pd.isnull(door_h):
        st.warning("Door dimensions are missing. Cannot verify door fit.")
        fits_door = False
    else:
        fits_door = ((part_length <= door_w and part_width <= door_h) or
                     (part_length <= door_h and part_width <= door_w))
    
    if fits_door:
        st.success("The cargo fits through the aircraft door.")
    else:
        st.error("The cargo does not fit through the aircraft door.")
    
    # Cabin Fit Check
    cab_l = selected_aircraft["Cabin Length (in)"]
    cab_w = selected_aircraft["Cabin Width (in)"]
    cab_h = selected_aircraft["Cabin Height (in)"]
    
    if pd.isnull(cab_l) or pd.isnull(cab_w) or pd.isnull(cab_h):
        st.warning("Cabin dimensions are missing. Cannot verify cabin fit.")
        cabin_fit = False
    else:
        cabin_fit = (
            part_length <= cab_l and
            part_width <= cab_w and
            part_height <= cab_h
        )
    
    if cabin_fit:
        st.success("The cargo fits within the cabin.")
    else:
        st.error("The cargo does not fit within the cabin dimensions.")
    
    st.markdown("---")
    
    # Visualization Section (Placeholder)
    st.subheader("Visualization")
    st.info("Visualization functionality coming soon! (e.g., 3D rotation and insertion path animation)")
