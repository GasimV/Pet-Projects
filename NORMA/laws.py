import time
import pandas as pd
from selenium.webdriver import Chrome, ChromeOptions
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import re
from stemmer.stemmer import Stemmer

from joblib import Parallel, delayed
from tqdm import tqdm

stemmer = Stemmer()
stop_words = stopwords.words("azerbaijani")
stop_words = stop_words + ["azərbaycan", "maddə", "respublika"]

options = ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')

def preprocessing(data:str):
    data = data.lower()
    data = re.sub(r'[^a-zA-ZƏəƏəĞğÖöŞşÇçÜüİı\s]', '', data)
    data = re.sub(r'\s+', ' ', data)
    data = re.sub(r'-+', '', data)
    data = data.replace("İ".lower(), "I".lower())
    data = stemmer.stem_words(data.split())
    data = len([i for i in data if i not in stop_words])
    return data

def process(data:pd.DataFrame) -> list[dict]:
    url = f"https://e-qanun.az/framework/{data['id']}"
    status = data['statusName']
    type = data['typeName']
    name = data['title']

    driver = Chrome(options=options)
    driver.get(url)
    time.sleep(10)
    page = driver.page_source
    driver.close()
    driver.quit()

    page = BeautifulSoup(page, "lxml").text
    page = re.sub(r'\xa0', '', page)
    page = re.sub(r'\n{1,}', '\n', page)
    last_string = page.split('\n')[-1]
    page = page[:page.find(last_string)]
    page = page[page.find(name):]

    lst = []
    # matches = re.findall(r'Maddə.*?(?=Maddə|$)', page, re.DOTALL)
    # if len(matches) > 0:
    #     for match in matches:
    #         lst.append({
    #             "url": url,
    #             "status": status,
    #             "type": type,
    #             "name": name,
    #             "text": match
    #         })
    #     return lst

    num_tokens = preprocessing(page)
    if num_tokens <= 512:
        lst.append({
            "url": url,
            "status": status,
            "type": type,
            "name": name,
            "text": page
        })
        return lst

    elif num_tokens > 512:
        pg = re.sub(r'\s+', ' ', page).split()
        pg = [lst[i:i + 512] for i in range(0, len(pg), 512)]
        pg = [''.join(chunk) for chunk in pg]

        for p in pg:
            lst.append({
                "url": url,
                "status": status,
                "type": type,
                "name": name,
                "text": p
            })
        return lst

for i in range(0, 8000, 2000):
    if i < 6000:
        data = pd.read_csv("../data/all_links.csv")
        data = data.loc[data["typeName"] == "AZƏRBAYCAN RESPUBLİKASI PREZİDENTİNİN FƏRMANLARI"].reset_index(drop=True)
        data = data.iloc[i:i+2000]
    elif i >= 6000:
        data = pd.read_csv("../data/all_links.csv")
        data = data.loc[data["typeName"] == "AZƏRBAYCAN RESPUBLİKASI PREZİDENTİNİN FƏRMANLARI"].reset_index(drop=True)
        data = data.iloc[i::]

    dt = Parallel(n_jobs=20)(delayed(process)(dt) for index, dt in tqdm(data.iterrows()))

    dt = [item for sublist in dt for item in sublist]

    data = pd.DataFrame(data=dt)
    data.to_parquet(f"../data/decrees_{i}.parquet", index=False)