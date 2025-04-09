import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.title("Water Quality Data Explorer")
st.write("Upload location and water quality databases to explore contaminant data.")

location_file = st.file_uploader("Upload Location Database (e.g., stations.csv)", type=["csv"])
wq_file = st.file_uploader("Upload Water Quality Database (e.g., results.csv)", type=["csv"])

# --- Define expected column names (you might need to adjust these) ---
LOCATION_ID_COL_LOC = "MonitoringLocationIdentifier"
LATITUDE_COL = "LatitudeMeasure"
LONGITUDE_COL = "LongitudeMeasure"
LOCATION_ID_COL_WQ = "MonitoringLocationIdentifier"
CONTAMINANT_COL = "CharacteristicName"
VALUE_COL = "ResultMeasureValue"
DATE_COL = "ActivityStartDate"

if location_file and wq_file:
    try:
        location_df = pd.read_csv(location_file)
        st.success("Location database uploaded successfully!")
    except Exception as e:
        st.error(f"Error loading location database: {e}")
        location_df = None

    try:
        wq_df = pd.read_csv(wq_file)
        st.success("Water quality database uploaded successfully!")
    except Exception as e:
        st.error(f"Error loading water quality database: {e}")
        wq_df = None

    if location_df is not None and wq_df is not None:
        unique_contaminants = wq_df[CONTAMINANT_COL].unique()
        selected_contaminant = st.selectbox("Select Contaminant", unique_contaminants)

        # --- Filter data for the selected contaminant ---
        contaminant_df = wq_df[wq_df[CONTAMINANT_COL] == selected_contaminant].copy()

        # --- Force Numeric Conversion and Drop NaNs for Value Column ---
        contaminant_df[VALUE_COL] = pd.to_numeric(contaminant_df[VALUE_COL], errors='coerce')
        contaminant_df.dropna(subset=[VALUE_COL], inplace=True)

        # --- Force Datetime Conversion and Drop NaTs for Date Column ---
        contaminant_df[DATE_COL] = pd.to_datetime(contaminant_df[DATE_COL], errors='coerce')
        contaminant_df.dropna(subset=[DATE_COL], inplace=True)

        st.write(f"Data type of VALUE_COL after conversion (contaminant_df): {contaminant_df[VALUE_COL].dtype}")
        st.write(f"Data type of DATE_COL after conversion (contaminant_df): {contaminant_df[DATE_COL].dtype}")
        st.write("First 20 rows of contaminant_df:")
        st.write(contaminant_df.head(20))

        # --- Value Range Input (Adjusted Slider) ---
        min_val_contaminant = float(contaminant_df[VALUE_COL].min()) if not contaminant_df[VALUE_COL].empty else 0.0
        max_val_contaminant = float(contaminant_df[VALUE_COL].max()) if not contaminant_df[VALUE_COL].empty else 1.0
        selected_range = st.slider(
            f"Select Value Range for {selected_contaminant}",
            min_value=min_val_contaminant,
            max_value=max_val_contaminant,
            value=(min_val_contaminant, max_val_contaminant),
        )
        min_val, max_val = selected_range

        # --- Date Range Input ---
        min_date = wq_df[DATE_COL].min()
        max_date = wq_df[DATE_COL].max()
        start_date = st.date_input("Start Date", min_date)
        end_date = st.date_input("End Date", max_date)

        # --- Data Filtering (Using the already cleaned contaminant_df) ---
        filtered_wq_df = contaminant_df[
            (contaminant_df[VALUE_COL] >= min_val) &
            (contaminant_df[VALUE_COL] <= max_val) &
            (contaminant_df[DATE_COL] >= pd.to_datetime(start_date)) &
            (contaminant_df[DATE_COL] <= pd.to_datetime(end_date))
        ].copy()

        st.write(f"Shape of filtered_wq_df: {filtered_wq_df.shape}")
        st.write(f"Data type of VALUE_COL in filtered_wq_df: {filtered_wq_df[VALUE_COL].dtype if not filtered_wq_df.empty else None}")
        st.write(f"Data type of DATE_COL in filtered_wq_df: {filtered_wq_df[DATE_COL].dtype if not filtered_wq_df.empty else None}")
        st.write("First 20 rows of filtered_wq_df:")
        st.write(filtered_wq_df.head(20) if not filtered_wq_df.empty else None)

        if not filtered_wq_df.empty:
            # --- Map Display ---
            merged_df = pd.merge(
                location_df,
                filtered_wq_df,
                left_on=LOCATION_ID_COL_LOC,
                right_on=LOCATION_ID_COL_WQ,
                how="inner",
            )

            if not merged_df.empty:
                st.subheader("Monitoring Stations with Selected Contaminant")
                try:
                    mid_lat = merged_df[LATITUDE_COL].mean()
                    mid_lon = merged_df[LONGITUDE_COL].mean()
                    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=10)
                    for index, row in merged_df.iterrows():
                        folium.Marker([row[LATITUDE_COL], row[LONGITUDE_COL]], popup=row[LOCATION_ID_COL_WQ]).add_to(m)
                    st_folium(m, width=700, height=500)
                except KeyError as e:
                    st.error(f"Error: Could not find latitude or longitude columns in the merged data: {e}")
            else:
                st.warning("No monitoring stations found with the selected contaminant in the specified range.")

            # --- Trend Plot Display ---
            st.subheader(f"Trend of {selected_contaminant} Over Time")
            fig, ax = plt.subplots(figsize=(10, 6))
            for site in filtered_wq_df[LOCATION_ID_COL_WQ].unique():
                site_data = filtered_wq_df[filtered_wq_df[LOCATION_ID_COL_WQ] == site].sort_values(by=DATE_COL)
                ax.plot(site_data[DATE_COL], site_data[VALUE_COL], label=site)

            ax.set_xlabel("Time")
            ax.set_ylabel(selected_contaminant)
            ax.legend(title="Station")
            ax.grid(True)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

        else:
            st.info(f"No data found for the selected contaminant within the specified value and date ranges.")

