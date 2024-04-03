import requests
from io import StringIO
import pandas as pd
import random
import time  # Importing time module for adding delay

def fetch_sensor_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = StringIO(response.text)

        # Adjusting skiprows to 3 based on the CSV structure
        df = pd.read_csv(csv_content, delimiter=';', header=0, skiprows=3)

        # Selecting the last row of the DataFrame
        last_row = df.iloc[-1]

        sensor_type = last_row['Process value']  # 'Process value' column contains the sensor type
        sensor_value = last_row['Measurement value']  # 'Measurement value' column contains the sensor value
        unit = last_row['Unit']  # Unit of measurement

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

def fetch_sensor_data_mock(url):
    sensor_value = round(random.uniform(1.5, 2.5), 3)
    return {
        "sensor_type": "Temperature",
        "value": sensor_value,
        "unit": "degC"
    }

def main():
    for _ in range(100):
        val = fetch_sensor_data("http://192.168.1.212/userfiles/Data0_logbook.csv")
        print(val)
        time.sleep(1)  # Adding a 1-second delay in each iteration

if __name__ == "__main__":
    main()
