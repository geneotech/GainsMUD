#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

URL = "https://debank.com/profile/0x4df1cc7459fd074cbc6aa8803cceaee561812fbe"


def get_gns_amount():
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    options.set_preference('permissions.default.image', 2)  # blokuj obrazki
    options.set_preference('javascript.enabled', True)
    options.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', False)
    options.set_preference('media.volume_scale', '0.0')
    options.page_load_strategy = 'eager'  # nie czekaj na pełne załadowanie

    driver = webdriver.Firefox(options=options)

    try:
        driver.get(URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.LINK_TEXT, "GNS"))
        )

        gns_link = driver.find_element(By.LINK_TEXT, "GNS")
        row = gns_link.find_element(By.XPATH, "./ancestor::div[contains(@class,'db-table-row')]")
        cells = row.find_elements(By.CLASS_NAME, "db-table-cell")

        for cell in cells:
            text = cell.text.strip()
            if re.match(r'^[\d,]+\.\d+$', text):
                return text.replace(',', '')
    finally:
        driver.quit()

    return None


if __name__ == '__main__':
    print(get_gns_amount())
