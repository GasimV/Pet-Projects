import os
from joblib import Parallel, delayed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
import time
import random

pages_in_data = np.array([int(i.split(".")[0]) for i in os.listdir("data/data")])
pages_not_in_data = np.array([i for i in range(1, 56557) if i not in pages_in_data])
pages = np.array([f"https://e-qanun.az/framework/{i}" for i in pages_not_in_data])

chrome_options = Options()
chrome_options.add_argument("--headless")

def run_selenium_task(url):
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        try:
            element = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "WordSection1")))
        except TimeoutException:
            pass

        try:
            element = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.CLASS_NAME, "Section1")))
        except TimeoutException:
            pass

        html = driver.page_source

        #with open(f"data/pages/{url.split('/')[-1]}.html", "w", encoding="utf-8") as file:
            #file.write(html)
            #file.close()

        soup = BeautifulSoup(html, "lxml")

        try:
            if soup.find("div", class_="WordSection1") is not None:
                content_part = soup.find("div", class_="WordSection1")
            elif soup.find("div", class_="Section1").find("div", class_="Section1") is not None:
                content_part = soup.find("div", class_="Section1").find("div", class_="Section1")
            elif soup.find("div", class_="Section1") is not None:
                content_part = soup.find("div", class_="Section1")
            elif soup.find("div", class_="WordSection2") is not None:
                content_part = soup.find("div", class_="WordSection2")
            elif soup.find("div", class_="Section3") is not None:
                content_part = soup.find("div", class_="Section3")
            elif soup.find("div", class_="Section4") is not None:
                content_part = soup.find("div", class_="Section4")
            elif soup.find("div", class_="WordSection3") is not None:
                content_part = soup.find("div", class_="WordSection3")


        except:
            pass

        content = []
        for _content in content_part:
            try:
                _class = content.get("class")
            except:
                _class = None

            if _class != "Bottomima" and _class != "BottomNo" and _class != "MsoNormal":
                if _content.text not in content:
                    content.append(_content.text)
            else:
                break

        data = pd.DataFrame()
        data["text"] = content
        data["text"] = data["text"].apply(lambda x: x.strip())
        data["len"] = data["text"].apply(lambda x: len(x))
        data = data.loc[data["len"] > 0].reset_index(drop=True)
        data["document_name"] = data["text"].loc[0]
        data["document_type"] = data["text"].loc[1]

        data.to_csv(f"data/data/{url.split('/')[-1]}.csv", index=False)

        driver.close()
        driver.quit()

        time.sleep(random.randint(1, 3))

    except Exception as ex:
        print(f"{ex}: {url}")

Parallel(n_jobs=-1)(delayed(run_selenium_task)(url) for url in tqdm(pages))