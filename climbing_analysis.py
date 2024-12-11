import streamlit as st
import pandas as pd
from scipy.signal import find_peaks
import altair as alt

# Constants
GRAVITY = 9.81  # Acceleration due to gravity in m/s^2
BODY_MASS = 60  # Your body mass in kg

uploaded_file = st.file_uploader("Choose a file")
if not uploaded_file:
    st.text("Please upload a file")
    st.stop()

data = pd.read_csv(uploaded_file, header=None)

# Assign column names for better readability
data.columns = ['timestamp', 'sample number', 'battRaw', 'samples', 'masses']

# Convert the timestamp to milliseconds
data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')

# Set the first timestamp as reference 0
data['timestamp'] = (data['timestamp'] - data['timestamp'].iloc[0]).dt.total_seconds() * 1000

# Convert the samples from kg to Newtons
data['samples'] = data['samples'] * GRAVITY

st.title('Climbing Data Analysis')

st.text('Raw Data Overview')
st.line_chart(data[['timestamp', 'samples']].set_index('timestamp'), x_label='Time (ms)', y_label='Force (N)')

# Find the peaks in the 'samples' column
peaks, _ = find_peaks(data['samples'])

# Extract the relevant columns: timestamp and signal
timestamps = data['timestamp']
signal = data['samples']

# Define a threshold for grouping peaks into plateaus (e.g., based on timestamp differences)
threshold = 5000  # Adjust this value depending on the spacing of your data

# Group peaks into plateaus
plateaus = []
current_plateau = [peaks[0]]

for i in range(1, len(peaks)):
    if timestamps.iloc[peaks[i]] - timestamps.iloc[peaks[i - 1]] < threshold:
        current_plateau.append(peaks[i])
    else:
        plateaus.append(current_plateau)
        current_plateau = [peaks[i]]
plateaus.append(current_plateau)

# Initialize a list to store the RFD results and lines for plotting
rfd_results = []
rfd_lines = []

for plateau in plateaus:
    # Get the indices of the current plateau
    highest_peak_idx = max(plateau, key=lambda idx: signal.iloc[idx])  # Index of the highest peak

    # Find the plateau start time (last point near 0 before the plateau begins)
    start_idx = plateau[0]
    for idx in range(start_idx - 1, -1, -1):
        if signal.iloc[idx] <= 0.1:  # Threshold for signal baseline (adjustable)
            start_idx = idx
            break

    # Calculate the time taken to reach the highest peak (in seconds)
    start_time = timestamps.iloc[start_idx]
    peak_time = timestamps.iloc[highest_peak_idx]
    time_to_peak = (peak_time - start_time) / 1000  # Convert milliseconds to seconds

    # Calculate the rate of force development (RFD)
    peak_value = signal.iloc[highest_peak_idx]
    rfd = peak_value / time_to_peak if time_to_peak > 0 else None  # Avoid division by zero

    # Store the results
    rfd_results.append({
        "Plateau Start Time": start_time,
        "Peak Time": peak_time,
        "Time to Peak (s)": time_to_peak,
        "Peak Value (kg)": peak_value / GRAVITY,  # Convert back to kg
        "Peak Value (N)": peak_value,
        "RFD (kg/s)": rfd / GRAVITY if rfd is not None else None,  # Convert back to kg/s
        "RFD (N/s)": rfd if rfd is not None else None,
    })

    # Store the line data for plotting
    rfd_lines.append({
        "start_time": start_time,
        "end_time": peak_time,
        "start_value": 0,
        "end_value": peak_value
    })

# Convert results to a DataFrame for better visualization
rfd_df = pd.DataFrame(rfd_results)
rfd_lines_df = pd.DataFrame(rfd_lines)

# Display the RFD results in the Streamlit app
st.text("Rate of Force Development (RFD) Results")
st.dataframe(rfd_df)

# Plot the highest peaks and RFD lines using Altair
peaks_chart = alt.Chart(rfd_df).mark_point(color='red', size=100).encode(
    x=alt.X('Peak Time', axis=alt.Axis(title='Time (ms)')),
    y=alt.Y('Peak Value (N)', axis=alt.Axis(title='Force (N)')),
    tooltip=[alt.Tooltip('Peak Time', title='Time (ms)'), alt.Tooltip('Peak Value (N)', title='Force (N)')]
)

# Add RFD labels
rfd_labels = alt.Chart(rfd_df).mark_text(align='left', dx=5, dy=-5, color='blue').encode(
    x=alt.X('Peak Time', axis=alt.Axis(title='Time (ms)')),
    y=alt.Y('Peak Value (N)', axis=alt.Axis(title='Force (N)')),
    text=alt.Text('RFD (N/s):Q', format='.2f')
)

# Combine the line chart, peaks chart, and RFD labels
combined_chart = alt.layer(
    alt.Chart(data).mark_line().encode(
        x=alt.X('timestamp', axis=alt.Axis(title='Time (ms)')),
        y=alt.Y('samples', axis=alt.Axis(title='Force (N)')),
        tooltip=[alt.Tooltip('timestamp', title='Time (ms)'), alt.Tooltip('samples', title='Force (N)')]
    ),
    peaks_chart,
    rfd_labels
).properties(
    title='Highest Peaks and RFD Calculation Lines',
)

# Display the combined chart in the Streamlit app
st.text("Display the highest values achieved in the climbing data, for a given measurement plateau")
st.altair_chart(combined_chart, use_container_width=True)