import streamlit as st
import requests
import csv
import base64
import pandas as pd
from datetime import datetime
import zipfile
import os

st.title("Awin Affiliate Report Generator")

# Load merchant IDs and access token
awin_config = st.secrets["awin"]
merchant_ids = awin_config["merchant_ids"]
access_token = awin_config["access_token"]

# Select merchant and date range
merchant = st.selectbox("Select Merchant", ["All"] + list(merchant_ids.keys()))
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")

# List to store all generated report filenames
generated_files = []

# Use columns to place buttons side by side
col1, col2 = st.columns([3, 1])  # [3, 1] means col1 takes 75% width and col2 takes 25% width

with col1:
    generate_report_button = st.button("Generate Report", key="generate_report")

# Initially, disable the "Download All" button
download_all_button = None  # Default is None, meaning the button will not show

# Handle "Generate Report" button action
if generate_report_button:
    selected = list(merchant_ids.keys()) if merchant == "All" else [merchant]

    for m in selected:
        st.write(f"📦 Fetching report for **{m}**...")
        merchant_id = merchant_ids[m]

        url = f"https://api.awin.com/advertisers/{merchant_id}/reports/publisher"
        params = {
            "accessToken": access_token,
            "dateType": "transaction",
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "timezone": "UTC"
        }

        response = requests.get(url, headers={"accept": "application/json"}, params=params)

        if response.status_code != 200:
            st.error(f"Failed for {m}: {response.status_code}")
            continue

        data = response.json()

        if not data:
            st.warning(f"No data for {m}")
            continue

        # Extract relevant fields
        filtered_data = [
            {
                "Publisher ID": d.get("publisherId"),
                "Publisher Name": d.get("publisherName"),
                "Clicks": d.get("clicks", 0),
                "# of Sales": d.get("totalNo"),
                "Total Value": f"${d.get('totalValue', 0.0)}",
                "Conv. Rate": f"{(d.get('totalNo', 0) / d.get('clicks', 1)) * 100:.2f}%"  # Rounded to 2 decimals and added %
            }
            for d in data
        ]

        # Sort by clicks, descending
        df = pd.DataFrame(filtered_data).sort_values("Clicks", ascending=False)

        # Display the report preview
        st.subheader(f"{m} report preview")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Save cleaned DataFrame to CSV
        filename = f"{m}_awin_report_{datetime.now().strftime('%Y-%m-%d')}.csv"
        df.to_csv(filename, index=False)

        # Append the merchant report details at the end of the CSV file
        with open(filename, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([])
            writer.writerow([f"Merchant report for {m} from {start_date} to {end_date}"])

        # Add the filename to the list of generated files
        generated_files.append(filename)

        # Download link for individual file
        with open(filename, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download {filename}</a>'
            st.markdown(href, unsafe_allow_html=True)

        st.success(f"✅ {filename} is ready.")

    # After reports are generated, enable the "Download All" button at the top
    st.markdown("---")  # Add a divider for separation
    download_all_button = True  # Set to True to enable the "Download All" button

# Handle the "Download All" button action
if download_all_button:
    # Create a zip file containing all the reports
    zip_filename = "awin_reports.zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        for file in generated_files:
            zipf.write(file, os.path.basename(file))

    # Provide a download link for the zip file
    with open(zip_filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
        href = f'<a href="data:file/zip;base64,{b64}" download="{zip_filename}">📥 Download All Reports</a>'
        st.markdown(href, unsafe_allow_html=True)
