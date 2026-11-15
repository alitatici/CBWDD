import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re


# Function to convert mm/dd/yyyy date to float year
def date_to_float(date_str):
    date = pd.to_datetime(date_str)
    year = date.year
    # Calculate the fraction of the month
    month_fraction = (date.month - 1) / 12
    # Calculate the fraction of the day within the current month
    days_in_month = (date + pd.offsets.MonthEnd(0)).day  # Last day of the month
    day_fraction = (date.day - 1) / days_in_month / 12  # Fraction of the month

    return year + month_fraction + day_fraction

df = pd.read_csv("<path to LCPA parcel list with a 'STRAP' column>")

dfScrapingData = pd.DataFrame(columns=["Municipality", "Latitude", "Longitude", "Use Code Description",
                                       "Number of Stories", "Year of Built", "Retrofit Year", "Roof Retrofit Year"])

permit_data_df_cumulative = pd.DataFrame()
number = 0

for index, row in df.iterrows():
    number += 1
    municipality = None
    latitude = None
    longitude = None
    UseCodeDescription = None
    stories = None
    yearBuilt = None
    RetrofitAge = None
    RoofRetrofitAge = None
    flag_detailsTable = 0

    driver = webdriver.Firefox()

    base_url = "https://www.leepa.org/Search/PropertySearch.aspx"
    search_term = row['STRAP']

    driver.get(base_url)
    time.sleep(3)

    search_box = driver.find_element(By.ID, "ctl00_BodyContentPlaceHolder_WebTab1_tmpl0_STRAPTextBox")

    search_box.clear()
    search_box.send_keys(search_term + Keys.RETURN)
    time.sleep(3)

    try:
        element = driver.find_element(By.CSS_SELECTOR, "[target='ParcelView']")
        element.click()

        time.sleep(3)
        driver.switch_to.window(driver.window_handles[-1])

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "appraisalDetailsLocation.autoAlternate")))

        '''
        Municipality, Latitude, Longitude
        '''

        table = driver.find_element(By.CLASS_NAME, "appraisalDetailsLocation.autoAlternate")
        rows = table.find_elements(By.TAG_NAME, "tr")

        try:
            if rows[2].text.split()[1] == 'Latitude' and rows[2].text.split()[2] == 'Longitude':
                try:
                    text = rows[3].text
                    match = re.match(r'(.+?)\s(-?\d+\.\d+)\s(-?\d+\.\d+)', text)
                    if match:
                        municipality = match.group(1)
                        latitude = match.group(2)
                        longitude = match.group(3)
                except:
                    municipality = text

            else:
                print("Control failed: Extracted values do not match expected from coordinates.")

        except Exception as e:
            print(f"An error occurred while extracting municipality and coordinate data from Parcel Details: {e}")


        '''
        Use Code Description
        '''
        element = driver.find_element(By.CSS_SELECTOR, "[id='AppraisalHyperLinkCurrent2']")
        element.click()
        time.sleep(3)
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "PropertyDetailsCurrent")))
        innerBox = WebDriverWait(container, 10).until(
            lambda container: container.find_elements(By.CLASS_NAME, "innerBox"))
        innerBox_first = innerBox[0]
        tableInnerBox = innerBox_first.find_element(By.CLASS_NAME, "appraisalAttributes")
        rows = tableInnerBox.find_elements(By.TAG_NAME, "tr")
        theRow = rows[2].text
        result = re.search(r'\d+\s(.*?)\s\d+\.\d+\s\w+', theRow)
        if result:
            UseCodeDescription = result.group(1)
        else:
            print("Could not extract Use Code Description from Parcel Details.")

        '''
        Year of Built, Number of Stories
        '''
        try:
            innerBox_second = innerBox[1]
            tableInnerBox = innerBox_second.find_element(By.CLASS_NAME, "appraisalAttributes")
            rows = tableInnerBox.find_elements(By.TAG_NAME, "tr")
            target_cell = rows[3].find_elements(By.TAG_NAME, "td")[2]
            stories = target_cell.text
            target_cell = rows[5].find_elements(By.TAG_NAME, "td")[2]
            yearBuilt = target_cell.text
        except Exception as e:
            print(f"An error occurred while extracting number of stories and year of built data from Parcel Details: {e}")

        '''
        Retrofit age, roof retrofit age
        '''
        try:
            permit_details = driver.find_element(By.CSS_SELECTOR, "#PermitDetails")
            permit_details.click()
            time.sleep(3) # Click if it reveals the table or triggers loading
        except Exception as e:
            flag_detailsTable = 1
            print(f"There is no Parcel Details: {e}")

        if flag_detailsTable == 0:
            try:
                table = driver.find_element(By.CLASS_NAME, "detailsTable")

                wait = WebDriverWait(driver, 10)

                # Locate the table within #PermitDetails with class 'detailsTable'
                tablePermitDetails = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#PermitDetails .detailsTable")))

                # Get the header row and retrieve text from each header cell
                header_row = tablePermitDetails.find_element(By.TAG_NAME, "tr")
                headers = [header.text for header in header_row.find_elements(By.TAG_NAME, "th")]

                # Retrieve all data rows within this specific table (excluding the header)
                data_rows = tablePermitDetails.find_elements(By.CSS_SELECTOR, "tr.even")  # Adjust if there's an odd/even pattern
                try:
                    data_rows_odd = tablePermitDetails.find_elements(By.CSS_SELECTOR, "tr.odd")
                    data_rows = data_rows + data_rows_odd
                except:
                    pass

                # Extract each row's data into a list
                table_permit_data = []
                for row in data_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")  # Get each cell in the row
                    row_data = [cell.text for cell in cells if cell.text.strip()]  # Collect non-empty text from each cell
                    if row_data:  # Only process non-empty rows
                        table_permit_data.append(row_data)

                # Create a DataFrame with headers and data
                permit_data_df = pd.DataFrame(table_permit_data, columns=headers)
                permit_data_df_cumulative = pd.concat([permit_data_df_cumulative, permit_data_df], ignore_index=True)

                '''
                Getting "Roof" and "Building New Construction" data from the "Building/Construction Permit Data" table.
                '''
                permit_data_df['Date'] = pd.to_datetime(permit_data_df['Date'], format='%m/%d/%Y')
                roof_permits = permit_data_df[permit_data_df['Permit Type'].isin(['Roof', 'Roof / Sheds'])]
                newest_roof_date = roof_permits['Date'].max()
                RoofRetrofitAge = date_to_float(newest_roof_date)

                retrofit_permits = permit_data_df[permit_data_df['Permit Type'].isin(['Building New Construction',
                                                                                      'Building Remodel / Repair'])]
                newest_retrofit_date = retrofit_permits['Date'].max()
                RetrofitAge = date_to_float(newest_retrofit_date)

            except Exception as e:
                print(f"An error occurred while extracting retrofit age and roof retrofit age data from Parcel Details: {e}")

        data = {
            'Municipality': [municipality],
            'Latitude': [latitude],
            'Longitude': [longitude],
            'Use Code Description': [UseCodeDescription],
            'Number of Stories': [stories],
            'Year of Built': [yearBuilt],
            'Retrofit Year': [RetrofitAge],
            'Roof Retrofit Year': [RoofRetrofitAge]
        }
        scrapingData = pd.DataFrame(data)
        dfScrapingData = pd.concat([dfScrapingData, scrapingData], ignore_index=True)
        driver.quit()

    except Exception as e:
        data = {
            'Municipality': [municipality],
            'Latitude': [latitude],
            'Longitude': [longitude],
            'Use Code Description': [UseCodeDescription],
            'Number of Stories': [stories],
            'Year of Built': [yearBuilt],
            'Retrofit Year': [RetrofitAge],
            'Roof Retrofit Year': [RoofRetrofitAge]
        }
        scrapingData = pd.DataFrame(data)
        dfScrapingData = pd.concat([dfScrapingData, scrapingData], ignore_index=True)
        driver.quit()
        print(f"Unknown error occurred: {e}")

    if number == 1:
        number = 0

        df_combined = pd.concat([df, dfScrapingData], axis=1)
        df_combined.to_csv("<path to output file>", index=False)

        try:
            permit_information = permit_data_df_cumulative.iloc[:, 1]
            unique_permit_data = pd.Series(permit_information.unique())
            unique_permit_data.reset_index(drop=True, inplace=True)
            unique_permit_data.to_csv("<path to unique permit types output file>", index=False)
        except:
            pass

print("fin")
