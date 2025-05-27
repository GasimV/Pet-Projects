import pandas as pd
import re
from tqdm import tqdm
import asyncio
import aiohttp
from random import randint
tqdm.pandas()
import time

data = pd.read_csv("data/result.csv")

def del_symbols(data:str):
    data = data.lower()
    data = re.sub(r'[^a-zA-ZəƏıIöÖüÜğĞçÇşŞ0-9-]', ' ', data)
    # data = re.sub(r'\n|\t|\s+', ' ', data)
    return data.strip()

async def translate_with_retry(text, src, dest, retries=3):
    for _ in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                # https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={dest}&dt=t&q={text}
                async with session.get(f"https://translate.google.com/?sl={src}&tl={dest}&text={text}&op=translate") as response:
                    if response.status == 200:
                        data = await response.json()
                        translated_text = data[0][0][0]
                        if translated_text is not None:
                            return {"az_text": text, "en_text": translated_text}
        except Exception as e:
            pass
        await asyncio.sleep(randint(5, 15))
    return {"az_text": text, "en_text": None}

data["text"] = data["text"].progress_apply(del_symbols)
data["document_name"] = data["document_name"].progress_apply(del_symbols)
data["document_type"] = data["document_type"].progress_apply(del_symbols)
data["len"] = data["text"].apply(lambda x: len(x.split()))
data = data.loc[data["len"] > 5].reset_index(drop=True)
data = data.loc[data["text"] != data["document_name"]].reset_index(drop=True)
data = data.loc[data["text"] != data["document_type"]].reset_index(drop=True)

data = data["text"].tolist()
start = time.time()
tasks = [translate_with_retry(text, "az", "en") for text in data[:10_000]]
data = None

async def translate_all():
    return await asyncio.gather(*tasks)

async def main():
    translated_texts = await translate_all()
    new_data = pd.DataFrame(translated_texts)
    new_data.to_csv("data/translated_data/az_to_en.csv", index=False)


asyncio.run(main())

finish = time.time()

print(print(f"Время выполнения: {(finish - start):.2f} секунд"))