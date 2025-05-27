from .models import ProductionQuery, FineTuningQuery
import os
import torch
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import numpy as np
import re
from openai import OpenAI
import tiktoken
from decouple import Config, RepositoryEnv
from django.conf import settings

# Paths to model and corpus file
corpus_path = os.path.join(settings.BASE_DIR, 'ai_queries/assets/corpus_embed.parquet')
model_path = os.path.join(settings.BASE_DIR, 'ai_queries/assets/final')

# Load the fine-tuned model
model = SentenceTransformer(model_path)

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Load the embeddings, texts, urls, and names from the corpus file
corpus_df = pd.read_parquet(corpus_path, engine='pyarrow')
embeddings = np.array(corpus_df['embeddings'].tolist())
texts = corpus_df['text'].tolist()
urls = corpus_df['url'].tolist()
names = corpus_df['name'].tolist()

# Specify the path to the .env file and load OpenAI API key
env_path = os.path.join(settings.BASE_DIR, '.env')
config = Config(RepositoryEnv(env_path))

# Fetch the OpenAI API key
openai_api_key = config('OPENAI_API_KEY')

# Initialize the OpenAI client using the API key
client = OpenAI(api_key=openai_api_key)


# Define constants
SIMILARITY_THRESHOLD = 0.75  # Adjust the threshold value as needed
MAX_TOKENS = 30_000  # Adjust if needed (the maximum allowed tokens for the input)


# Clean query by removing unwanted symbols
def clean_query(query):
    return re.sub(r'[\d!?.,;]*$', '', query).strip()


# Function to compute semantic similarity
def compute_similarity(query, embeddings, top_k=20):
    query_embedding = model.encode(query, convert_to_tensor=False)
    similarities = util.cos_sim(query_embedding, embeddings).cpu().numpy().flatten()
    results = []
    seen_texts = set()
    for i, score in enumerate(similarities):
        if score >= SIMILARITY_THRESHOLD and texts[i] not in seen_texts:
            seen_texts.add(texts[i])
            results.append({
                "query": query,
                "text": texts[i],
                "similarity_score": score,
                "url": urls[i],
                "name": names[i]
            })
    results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:top_k]
    return results


# Function to count tokens
def count_tokens(text, model_="gpt-4o-2024-08-06"):
    tokenizer = tiktoken.encoding_for_model(model_)
    return len(tokenizer.encode(text))


# Main function for handling searches and generating the final response
def handle_user_query(user_input):
    cleaned_query = clean_query(user_input)

    # Step 1: Construct the full prompt using semantic search
    top_k = 20
    text_search_limit = None
    full_prompt = None

    while True:
        try:
            # Filter corpus using a text search
            text_search_results = corpus_df[corpus_df['text'].str.contains(cleaned_query, case=False)]
            if text_search_limit is not None:
                text_search_results = text_search_results[:text_search_limit]

            # Compute similarity results
            similarity_results = compute_similarity(cleaned_query, embeddings, top_k=top_k)
            similarity_df = pd.DataFrame(similarity_results)

            # Combine text search and similarity results
            combined_results = pd.concat([text_search_results, similarity_df]).drop_duplicates(
                subset=['text', 'url', 'name'])

            # Construct the full prompt
            prompt = f"User Query: {cleaned_query}\n\nRetrieved Text Passages:\n\n"
            for _, row in combined_results.iterrows():
                prompt += f"Document Name: {row['name']}\nText: {row['text']}\nURL: {row['url']}\n" + "-" * 50 + "\n"

            # Check token count
            token_count = count_tokens(prompt)
            if token_count <= MAX_TOKENS:
                full_prompt = prompt
                break  # Exit loop if within token limit

            # Adjust parameters to reduce token count
            top_k = max(5, top_k - 5)
            if text_search_limit is None:
                text_search_limit = 10  # Apply an initial limit if previously unlimited
            else:
                text_search_limit = max(5, text_search_limit - 5)

        except Exception as e:
            raise Exception(f"Error during query preparation: {e}")

    # Step 2: Check for an existing entry in the ProductionQuery table
    existing_entry = ProductionQuery.objects.filter(full_prompt=full_prompt).first()
    if existing_entry:
        # Return cached response if match is found
        return existing_entry.gpt_response

    # Step 3: Generate response if no match is found
    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system",
                 "content": "You are an Azerbaijani lawyer who provides legal advice strictly based on Azerbaijani legislation. Always respond in Azerbaijani. Refer to relevant legal acts by the URL formatted as [text](URL) and their specific clauses, by ensuring the document name matches the [text] you provide and if you don't know the URL (it is not provided in the prompt) - don't provide it, because it can be false one, and suggest rephrase your query so that the system can better find the acts and articles it needs! Provide comprehensive response. If there are no relevant text passages among retrieved ones, discard them and base your answer on your own to address the user query!"},
                {"role": "user", "content": full_prompt}
            ]
        )
        gpt_response = response.choices[0].message.content

        # Step 4: Save the new full prompt and response to the ProductionQuery table
        ProductionQuery.objects.create(full_prompt=full_prompt, gpt_response=gpt_response)

        # Step 5: Save the user query and response to the FineTuningQuery table
        FineTuningQuery.objects.create(query_text=user_input, gpt_response=gpt_response)

        return gpt_response
    except Exception as e:
        raise Exception(f"Error during OpenAI API call: {e}")
