import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# ---------------------------
# Configuration and Logo
# ---------------------------
st.image("OFA_Gold_Black.png", width=200)
st.title("OnFly Air Cargo Fit Tool")
st.markdown("This app determines if a specified piece of cargo fits into the selected aircraft based on dimensions and payload limits.")

# ---------------------------
# Load Data Functions
# ---------------------------

# URL to the published Aircraft CSV
csv_url = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?output=csv"
)

@st.cache_data
def load_aircraft_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]
        numeric_columns = [
            "Door Width (in)", "Door Height (in)",
            "Cabin Length (in)", "Cabin Width (in)", "Cabin Height (in)",
            "Max Payload (lbs)", "Number of Seats", "Removable Seats",
            "Seat Weight (lbs)", "Seat Length (in)", "Seat Width (in)", "Seat Height (in)"
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "", regex=False)
                df[col] = df[col].str.replace("~", "", regex=False)
                df[col] = df[col].str.strip()
                if col == "Removable Seats":
                    df[col] = df[col].replace({"Yes": "2", "No": "0"})
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error loading aircraft data: {e}")
        return pd.DataFrame()

# URL for the Historical Parts CSV – UPDATE THIS WITH YOUR ACTUAL URL
historical_parts_csv_url = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vYOUR_HISTORICAL_PARTS_URL/pub?gid=YOUR_GID&output=csv"
)

@st.cache_data
def load_historical_parts(url):
    try:
        df = pd.read_csv(url)
        df.columns = [col.strip() for col in df.columns]
        # Expected columns: "Part Name", "Length (in)", "Width (in)", "Height (in)", "Weight (lbs)"
        numeric_columns = ["Length (in)", "Width (in)", "Height (in)", "Weight (lbs)"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "", regex=False)
                df[col] = df[col].str.replace("~", "", regex=False)
                df[col] = df[col].str.strip()
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error loading historical parts data: {e}")
        return pd.DataFrame()

df_aircraft = load_aircraft_data(csv_url)
df_hist_parts = load_historical_parts(historical_parts_csv_url)

# ---------------------------
# Step 1: Aircraft Selection
# ---------------------------
if df_aircraft.empty:
    st.error("Aircraft data could not be loaded. Please check your network connection or spreadsheet settings.")
else:
    st.header("Step 1: Select an Aircraft")
    aircraft_options = df_aircraft["Aircraft"].dropna().unique()
    selected_aircraft_model = st.selectbox("Select Aircraft", options=aircraft_options)
    selected_aircraft = df_aircraft[df_aircraft["Aircraft"] == selected_aircraft_model].iloc[0]
    
    st.subheader("Selected Aircraft Details")
    st.write(f"**Aircraft:** {selected_aircraft['Aircraft']}")
    st.write(
        f"**Cargo Door Dimensions:** {selected_aircraft['Door Width (in)']} in (W) x {selected_aircraft['Door Height (in)']} in (H)"
    )
    st.write(
        f"**Cabin Dimensions:** {selected_aircraft['Cabin Length (in)']} in (L) x {selected_aircraft['Cabin Width (in)']} in (W) x {selected_aircraft['Cabin Height (in)']} in (H)"
    )
    st.write(f"**Max Payload:** {selected_aircraft['Max Payload (lbs)']} lbs")
    st.write(
        f"**Seats:** {int(selected_aircraft['Number of Seats'])} (Removable: {int(selected_aircraft['Removable Seats'])})"
    )
    st.write(
        f"**Seat Info:** Weight: {selected_aircraft['Seat Weight (lbs)']} lbs, Dimensions: {selected_aircraft['Seat Length (in)']} x {selected_aircraft['Seat Width (in)']} x {selected_aircraft['Seat Height (in)']} in"
    )
    
    st.markdown("---")
    
    # ---------------------------
    # Step 2: Cargo (Part) Input & Historical Parts Dropdown
    # ---------------------------
    st.header("Step 2: Enter Cargo (Part) Details")
    
    # Always display dropdown with historical parts.
    if df_hist_parts.empty:
        st.info("No historical parts data available. Please add entries in the 'Historical Parts' tab.")
        hist_part_options = ["(None)"]
    else:
        # Create a sorted list of historical part names with "(None)" as the first option.
        hist_part_options = ["(None)"] + sorted(df_hist_parts["Part Name"].dropna().unique().tolist())
    
    selected_hist_part = st.selectbox(
        "Select a Historical Part (optional)",
        options=hist_part_options,
        index=0
    )
    
    # Manual entry inputs (user can override historical part selection)
    part_name_input = st.text_input("Enter New Part Name (if different from historical selection)", value="")
    col1, col2, col3 = st.columns(3)
    with col1:
        part_length = st.number_input("Length (in)", min_value=0.0, value=0.0, step=0.1)
    with col2:
        part_width = st.number_input("Width (in)", min_value=0.0, value=0.0, step=0.1)
    with col3:
        part_height = st.number_input("Height (in)", min_value=0.0, value=0.0, step=0.1)
    part_weight = st.number_input("Weight (lbs)", min_value=0.0, value=0.0, step=1.0)
    
    # Button to load the selected historical part's data
    if selected_hist_part != "(None)":
        if st.button("Load Selected Historical Part"):
            rec = df_hist_parts[df_hist_parts["Part Name"] == selected_hist_part].iloc[0]
            # Write the values to st.session_state so they persist (if needed)
            st.session_state["historical_part_loaded"] = {
                "Part Name": selected_hist_part,
                "Length": rec["Length (in)"],
                "Width": rec["Width (in)"],
                "Height": rec["Height (in)"],
                "Weight": rec["Weight (lbs)"]
            }
            st.experimental_rerun()
    
    # If a historical part was loaded (saved in session state), use its values
    if "historical_part_loaded" in st.session_state:
        loaded_part = st.session_state["historical_part_loaded"]
        final_part_name = loaded_part["Part Name"]
        part_length = loaded_part["Length"]
        part_width = loaded_part["Width"]
        part_height = loaded_part["Height"]
        part_weight = loaded_part["Weight"]
    else:
        final_part_name = part_name_input.strip() if part_name_input.strip() != "" else "(No Name)"
    
    st.write(f"**Final Part Name:** {final_part_name}")
    
    st.markdown("---")
    
    # ---------------------------
    # Step 3: Save/Load Parts (Optional)
    # ---------------------------
    st.header("Step 3: Save/Load Parts")
    if "saved_parts" not in st.session_state:
        st.session_state.saved_parts = {}
    if st.button("Save Part"):
        st.session_state.saved_parts[final_part_name] = {
            "Length": part_length,
            "Width": part_width,
            "Height": part_height,
            "Weight": part_weight
        }
        st.success(f"Saved part: {final_part_name}")
    if st.session_state.saved_parts:
        saved_options = list(st.session_state.saved_parts.keys())
        saved_selected = st.selectbox("Select a saved part to load values", options=["(None)"] + saved_options)
        if saved_selected != "(None)" and st.button("Load Selected Saved Part"):
            loaded = st.session_state.saved_parts[saved_selected]
            part_length = loaded["Length"]
            part_width = loaded["Width"]
            part_height = loaded["Height"]
            part_weight = loaded["Weight"]
            st.info(f"Loaded part: {saved_selected}")
    
    st.markdown("---")
    
    # ---------------------------
    # Step 4: Mission Feasibility Calculation
    # ---------------------------
    st.header("Step 4: Mission Feasibility Calculation")
    mechanics_travel = st.checkbox("Include mechanics in payload calculation")
    num_mechanics = st.number_input("Number of Mechanics", min_value=1, value=1, step=1) if mechanics_travel else 0
    avg_mech_weight = st.number_input("Average Weight per Mechanic (lbs)", min_value=0.0, value=180.0, step=1.0) if mechanics_travel else 0.0
    tool_weight = st.number_input("Total Tool Weight (lbs)", min_value=0.0, value=0.0, step=1.0) if mechanics_travel else 0.0
    
    total_cargo_weight = part_weight + (num_mechanics * avg_mech_weight) + tool_weight
    seat_weight = selected_aircraft.get("Seat Weight (lbs)", float('nan'))
    additional_payload = seats_removed * seat_weight if seats_removed > 0 and pd.notnull(seat_weight) else 0
    max_payload = selected_aircraft["Max Payload (lbs)"]
    available_payload = max_payload + additional_payload if pd.notnull(max_payload) else float('nan')
    
    st.write(f"**Total Required Payload Weight:** {total_cargo_weight:.2f} lbs")
    st.write(f"**Available Payload:** {available_payload:.2f} lbs")
    if pd.notnull(available_payload):
        if total_cargo_weight <= available_payload:
            st.success("Payload check: Within available limits!")
        else:
            st.error("Payload check: Over weight!")
    else:
        st.info("Payload check cannot be performed (missing data).")
    
    door_w = selected_aircraft["Door Width (in)"]
    door_h = selected_aircraft["Door Height (in)"]
    fits_door = False
    if pd.isnull(door_w) or pd.isnull(door_h):
        st.warning("Door dimensions are missing. Cannot verify door fit.")
    else:
        fits_door = ((part_length <= door_w and part_width <= door_h) or (part_length <= door_h and part_width <= door_w))
    
    if fits_door:
        st.success("The cargo fits through the aircraft door.")
    else:
        st.error("The cargo does not fit through the aircraft door.")
    
    cab_l = selected_aircraft["Cabin Length (in)"]
    cab_w = selected_aircraft["Cabin Width (in)"]
    cab_h = selected_aircraft["Cabin Height (in)"]
    cabin_fit = False
    if pd.isnull(cab_l) or pd.isnull(cab_w) or pd.isnull(cab_h):
        st.warning("Cabin dimensions are missing. Cannot verify cabin fit.")
    else:
        cabin_fit = (part_length <= cab_l and part_width <= cab_w and part_height <= cab_h)
    
    if cabin_fit:
        st.success("The cargo fits within the cabin.")
    else:
        st.error("The cargo does not fit within the cabin dimensions.")
    
    st.markdown("---")
    
    # ---------------------------
    # Step 5: Visualization (Static Mockup)
    # ---------------------------
    st.header("Step 5: Visualization")
    st.markdown(
        "Below is a mockup comparing the cargo dimensions to the door. The door is drawn as a blue rectangle starting at (0,0), "
        "and the cargo as an outline starting at (0,0). Green means it fits; red means it exceeds the door dimensions."
    )
    
    def create_cargo_visualization(door_w, door_h, cargo_length, cargo_width):
        fig, ax = plt.subplots(figsize=(6,6))
        door_rect = plt.Rectangle((0, 0), door_w, door_h, edgecolor='blue', facecolor='none', lw=2)
        ax.add_patch(door_rect)
        color = "green" if (cargo_length <= door_w and cargo_width <= door_h) else "red"
        cargo_rect = plt.Rectangle((0, 0), cargo_length, cargo_width, edgecolor=color, facecolor='none', lw=2)
        ax.add_patch(cargo_rect)
        ax.set_xlim(0, max(door_w, cargo_length) + 10)
        ax.set_ylim(0, max(door_h, cargo_width) + 10)
        ax.set_xlabel("inches")
        ax.set_ylabel("inches")
        ax.set_title("Door vs. Cargo Dimensions")
        ax.set_aspect("equal")
        return fig
    
    if pd.notnull(door_w) and pd.notnull(door_h):
        fig = create_cargo_visualization(door_w, door_h, part_length, part_width)
        st.pyplot(fig)
    else:
        st.info("Door dimensions unavailable; cannot display visualization.")
    
    st.markdown("---")
    st.header("Notes")
    st.markdown("The visualization above compares cargo dimensions to door dimensions. A green outline means the cargo fits; a red outline means it does not.")
