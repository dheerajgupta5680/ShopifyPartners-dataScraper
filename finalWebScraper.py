from numpy import empty
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import gspread

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("window-size=1280x720")

# Initialize the Chrome WebDriver
driver = webdriver.Chrome(options=chrome_options)


# Open one extra tab for loading partner details
driver.execute_script("window.open('');")
main_window = driver.window_handles[0]
details_window = driver.window_handles[1]

# Lists to store the scraped data
Web, names, urls, phone_numbers, email_addresses, locations = [], [], [], [], [], []

wait = WebDriverWait(driver, 1)

def safe_fetch_element(by, value, retries=3):
    last_exception = None
    for _ in range(retries):
        try:
            return wait.until(EC.visibility_of_element_located((by, value))).text
        except Exception as e:
            last_exception = e
            print(f"Retry fetching element: {value}")
    print(f"Element not found after retries: {value}")
    print(f"Last exception: {last_exception}")
    return 'Not found'

def load_gspread(Authfile, docUrl):
    gc = gspread.service_account(filename=Authfile)
    spreadsheet  = gc.open_by_url(docUrl)
    sheet = spreadsheet.sheet1
    existing_records = sheet.get_all_records()
    existing_df = pd.DataFrame(existing_records)
    return sheet, existing_df
    
def main():
    Authfile = 'shopifypartnersdata-fa2780c2f78c.json'
    docUrl = 'https://docs.google.com/spreadsheets/d/1zpWhEfvGexecgirjgQRIxVs_Y4YeQ5roaoNJZcEh8jw/edit?usp=sharing'
    
    Main_URL = 'https://www.shopify.com/partners/directory/services?'
    driver.get(Main_URL)
    page = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#main > section > form > div > div.col-span-4.xs\:col-span-12.md\:col-span-8.xs\:col-start-1.md\:col-start-5 > div > div.flex-auto.flex.max-w-fit.items-center.self-center.mt-6 > div > div > a:nth-child(5)')))
    last_page = int(page.text)
    try:
        for i in range(1, last_page):
            URL = f'https://www.shopify.com/partners/directory/services?page={i}'
            print(f'Retreiving data from page no.{i}')
            driver.get(URL)
            partner_elements = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, 'html > body > div:nth-of-type(2) > main > section > form > div > div:nth-of-type(2) > div > div > a[href]')))
            for element in partner_elements:
                url = element.get_attribute('href')
                Web.append(url)
                driver.switch_to.window(details_window)
                driver.get(url)
                
                # Extract details
                try:
                    name = safe_fetch_element(By.CSS_SELECTOR, "div.grid.gap-y-3 h1.richtext")
                    url_ele = safe_fetch_element(By.CSS_SELECTOR, "div.flex.flex-wrap.gap-x-2.items-center p.richtext.break-word a[rel='nofollow']")
                    phone = safe_fetch_element(By.CSS_SELECTOR, "div.flex.flex-wrap.gap-x-2.items-center p.richtext.break-word a[href^='tel']")
                    email = safe_fetch_element(By.CSS_SELECTOR, "div.flex.flex-wrap.gap-x-2.items-center p.richtext.break-word a[href^='mailto']")
                    location = safe_fetch_element(By.XPATH , "//div[contains(@class, 'flex') and contains(@class, 'flex-col') and contains(@class, 'gap-y-1')]/p[contains(@class, 'richtext') and contains(@class, 'text-t7') and contains(text(), 'Primary location')]/following-sibling::p[contains(@class, 'richtext')]")

                    names.append(name)
                    urls.append(url_ele)
                    phone_numbers.append(phone)
                    email_addresses.append(email)
                    locations.append(location)
                
                except Exception as e:
                    print(f"Failed to extract details for {url}: {e}")
                    names.append('Not found')
                    urls.append('Not found')
                    phone_numbers.append('Not found')
                    email_addresses.append('Not found')
                    locations.append('Not found')
                    
                # Switch back to the main window
                driver.switch_to.window(main_window)      

    except Exception as e:
        print(f"An error occurred during processing: {e}")

    finally:
        data = {
        "Name": names,
        "URL": urls,
        "Phone Number": phone_numbers,
        "Email Address": email_addresses,
        "Location": locations,
        "URL's": Web
        }
        df = pd.DataFrame(data)
        sheet, existing_df = load_gspread(Authfile, docUrl)
        new_data =  df[~df['Name'].isin(existing_df['Name'])]
        
        if not new_data.empty:
            data_to_insert = new_data.values.tolist()
            next_row = len(existing_df) + 2
            sheet.insert_rows(data_to_insert, next_row)
        driver.quit()

if __name__ == "__main__":
    main()
