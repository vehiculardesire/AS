import requests
from io import StringIO
import pandas as pd


def fetch_sensor_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = StringIO(response.text)

        # Skipping initial non-data lines to directly read the CSV data part
        # Adjust `skiprows` as needed based on the CSV structure
        df = pd.read_csv(csv_content, delimiter=';', header=0, skiprows=2)

        # Selecting the last row of the DataFrame
        last_row = df.iloc[-1]

        sensor_type = last_row['Process value']  # Assuming 'Process value' column contains the sensor type
        sensor_value = last_row['Measurement value']  # Assuming 'Measurement value' contains the sensor value
        unit = last_row['Unit']  # Unit of measurement

        # Converting sensor_value to float if it's in exponential format
        sensor_value = float(sensor_value)

        return {
            "sensor_type": sensor_type,
            "value": sensor_value,
            "unit": unit
        }

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except ValueError as ve:
        print(ve)
    except Exception as err:
        print(f"An error occurred: {err}")
    return None
