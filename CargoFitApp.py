import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import io

# Display the OnFly Air logo (ensure this file is in the repo's root)
st.image("OFA_Gold_Black.png", width=200)

st.title("OnFly Air Cargo Fit Tool")
st.markdown("This app determines if a specified piece of cargo fits into the selected aircraft based on dimensions and payload limits.")

# URL to the published Google Sheet CSV
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKEEZ-L7HCLpLtJ77O_NIgZpVjKOnxVrzts1p19KGGvFX4iLinJlnFlPNlQNcSZA2tO0PP6qIkk49-/pub?output=csv"

@st.cache_data
def load_aircraft_data(url):
    try:
        df = pd.read_csv(url)
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        # Process numeric columns: remove commas, tildes, extra spaces.
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

# Load aircraft specifications
df_aircraft = load_aircraft_data(csv_url)

if df_aircraft.empty:
    st.error("Aircraft data could not be loaded. Please check your network connection or spreadsheet settings.")
else:
    # ---------------------------
    # Step 1: Aircraft Selection
    # ---------------------------
    st.header("Step 1: Select an Aircraft")
    aircraft_options = df_aircraft["Aircraft"].dropna().unique()
    selected_aircraft_model = st.selectbox("Select Aircraft", options=aircraft_options)
    selected_aircraft = df_aircraft[df_aircraft["Aircraft"] == selected_aircraft_model].iloc[0]
    
    st.subheader("Selected Aircraft Details")
    st.write(f"**Aircraft:** {selected_aircraft['Aircraft']}")
    st.write(f"**Cargo Door Dimensions:** {selected_aircraft['Door Width (in)']} in (W) x {selected_aircraft['Door Height (in)']} in (H)")
    st.write(f"**Cabin Dimensions:** {selected_aircraft['Cabin Length (in)']} in (L) x {selected_aircraft['Cabin Width (in)']} in (W) x {selected_aircraft['Cabin Height (in)']} in (H)")
    st.write(f"**Max Payload:** {selected_aircraft['Max Payload (lbs)']} lbs")
    st.write(f"**Seats:** {int(selected_aircraft['Number of Seats'])} (Removable: {int(selected_aircraft['Removable Seats'])})")
    st.write(f"**Seat Info:** Weight: {selected_aircraft['Seat Weight (lbs)']} lbs, Dimensions: {selected_aircraft['Seat Length (in)']} x {selected_aircraft['Seat Width (in)']} x {selected_aircraft['Seat Height (in)']} in")
    
    st.markdown("---")
    
    # ---------------------------
    # Step 2: Cargo (Part) Input
    # ---------------------------
    st.header("Step 2: Enter Cargo (Part) Details")
    part_name = st.text_input("Part Name")
    col1, col2, col3 = st.columns(3)
    with col1:
        part_length = st.number_input("Length (in)", min_value=0.0, value=0.0, step=0.1)
    with col2:
        part_width = st.number_input("Width (in)", min_value=0.0, value=0.0, step=0.1)
    with col3:
        part_height = st.number_input("Height (in)", min_value=0.0, value=0.0, step=0.1)
    part_weight = st.number_input("Weight (lbs)", min_value=0.0, value=0.0, step=1.0)
    
    mechanics_travel = st.checkbox("Are mechanics traveling?")
    if mechanics_travel:
        num_mechanics = st.number_input("Number of Mechanics", min_value=1, value=1, step=1)
        avg_mech_weight = st.number_input("Average Weight per Mechanic (lbs)", min_value=0.0, value=180.0, step=1.0)
        tool_weight = st.number_input("Total Tool Weight (lbs)", min_value=0.0, value=0.0, step=1.0)
    else:
        num_mechanics = 0
        avg_mech_weight = 0.0
        tool_weight = 0.0
    
    remove_seat = st.checkbox("Remove a seat (cargo-only flight)?")
    if remove_seat:
        max_removable = selected_aircraft.get("Removable Seats", 0)
        max_removable = int(max_removable) if pd.notnull(max_removable) else 0
        seats_removed = st.number_input("Number of Seats to Remove", min_value=1, max_value=max_removable if max_removable > 0 else 1, value=1, step=1)
    else:
        seats_removed = 0
    
    st.markdown("---")
    
    # ---------------------------
    # Step 3: Save/Load Parts (Optional)
    # ---------------------------
    st.header("Step 3: Save/Load Parts")
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
    
    # ---------------------------
    # Step 4: Mission Feasibility Calculation
    # ---------------------------
    st.header("Step 4: Mission Feasibility Calculation")
    total_cargo_weight = part_weight + (num_mechanics * avg_mech_weight) + tool_weight
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
    st.write(f"**Available Payload:** {available_payload:.2f} lbs")
    if pd.notnull(available_payload):
        if total_cargo_weight <= available_payload:
            st.success("Payload check: Within available limits!")
        else:
            st.error("Payload check: Over weight!")
    else:
        st.write("Payload check: Cannot be performed (missing data).")
    
    door_w = selected_aircraft["Door Width (in)"]
    door_h = selected_aircraft["Door Height (in)"]
    fits_door = False
    if pd.isnull(door_w) or pd.isnull(door_h):
        st.warning("Door dimensions are missing. Cannot verify door fit.")
    else:
        fits_door = ((part_length <= door_w and part_width <= door_h) or
                     (part_length <= door_h and part_width <= door_w))
    
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
    # Step 5: Visualization and Animation
    # ---------------------------
    st.header("Step 5: Visualization and Animation")
    st.markdown("Below is an animated visualization of the cargo moving through the door.")
    
    def create_cargo_animation(door_w, door_h, cargo_length, cargo_width, frames=20):
        fig, ax = plt.subplots(figsize=(6,6))
        ax.set_xlim(0, max(door_w, cargo_length) + 10)
        ax.set_ylim(0, max(door_h, cargo_width) + 10)
        ax.set_xlabel("inches")
        ax.set_ylabel("inches")
        ax.set_title("Cargo Animation: Moving Through Door")
        
        # Draw the door rectangle (blue)
        door_rect = plt.Rectangle((0, 0), door_w, door_h, edgecolor='blue', facecolor='none', lw=2)
        ax.add_patch(door_rect)
        
        # Start the cargo rectangle to the left of the door
        cargo_rect = plt.Rectangle((-cargo_length, (door_h - cargo_width) / 2), cargo_length, cargo_width,
                                     edgecolor='green', facecolor='none', lw=2)
        ax.add_patch(cargo_rect)
        
        def update(frame):
            # Slide the cargo from left (off-screen) to the right (past the door)
            new_x = -cargo_length + frame * (door_w + cargo_length) / frames
            cargo_rect.set_x(new_x)
            return (cargo_rect,)
        
        ani = FuncAnimation(fig, update, frames=frames, interval=200, blit=True)
        buf = io.BytesIO()
        writer = PillowWriter(fps=5)
        # Remove the format parameter
        ani.save(buf, writer=writer)
        buf.seek(0)
        plt.close(fig)
        return buf

    if pd.notnull(door_w) and pd.notnull(door_h):
        cargo_animation_buf = create_cargo_animation(door_w, door_h, part_length, part_width)
        st.image(cargo_animation_buf, caption="Animation: Cargo Moving Through Door")
    else:
        st.info("Door dimensions unavailable; cannot display animation.")
    
    st.markdown("---")
    st.header("Notes")
    st.markdown("The animation shows how the cargo moves through the door. Green indicates a proper fit during the movement.")
