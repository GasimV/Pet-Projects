import pandas as pd
from tqdm import tqdm
from transformers import pipeline
import time
tqdm.pandas()

az_to_en = pd.read_csv("data/translated_data/az_to_en.csv")
az_to_en = az_to_en.dropna(axis=0).reset_index(drop=True)

pipe = pipeline("summarization", model="csebuetnlp/mT5_multilingual_XLSum", device="cuda")
az_to_en["en_text"] = az_to_en["en_text"].apply(lambda x: str(x).lower())
text = az_to_en["en_text"].tolist()

start = time.time()
result = pipe(text, batch_size=32)
finish = time.time()
print(f"Время выполнения: {(finish - start):.2f} секунд")

az_to_en["en_query"] = result
az_to_en.to_csv("data/translated_data/az_to_en.csv", index=False)