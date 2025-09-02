import os
import google.generativeai as genai
import faiss
import numpy as np
import pickle
from dotenv import load_dotenv

# .env faylından API Key yükləyək
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# API açarını konfiqurasiyası
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"API açarı konfiqurasiya edilərkən xəta baş verdi: {e}")
    print("Zəhmət olmasa `.env` faylında GOOGLE_API_KEY dəyərini yoxlayın.")
    exit()


class QASystem:
    def __init__(self, index_path='law_embeddings.faiss', chunks_path='chunks_for_retrieval.pkl'):
        """
        Sual-Cavab sistemini başladır, FAISS indeksini və mətn hissələrini yaddaşa yükləyir.
        """
        try:
            self.index = faiss.read_index(index_path)
            with open(chunks_path, 'rb') as f:
                self.chunks_data = pickle.load(f)
        except FileNotFoundError as e:
            print(f"Xəta: Fayl tapılmadı - {e}. `embedding_generator` skriptini işə saldığınıza əmin olun.")
            exit()

        self.embedding_model = 'models/gemini-embedding-001'

        # Təhlükəsizlik filtrlərini konfiqurasiya edirik
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        self.llm = genai.GenerativeModel('gemini-2.5-flash')
        print("Sual-Cavab sistemi uğurla yükləndi.")

    def _normalize_text(self, text: str) -> str:
        """
        İstifadəçi daxiletməsindəki potensial latın hərflərini Azərbaycan əlifbasına uyğunlaşdırır.
        """
        text = text.lower()
        replacements = {
            'sh': 'ş', 'ch': 'ç', 'gh': 'ğ', 'ü': 'u', 'ö': 'o',
            'ı': 'i', 'ə': 'e'  # Bəzən tərsinə də axtarış olur
        }
        # Bu əvəzləmə sadədir, daha mürəkkəb alqoritmlər tətbiq edilə bilər.
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def answer_question(self, question: str) -> str:
        """
        Verilmiş suala RAG arxitekturası ilə cavab generasiya edir.
        """
        try:
            # 1. Sualı emal et və vektorlaşdır
            # normalized_question = self._normalize_text(question) # Normallaşdırma bəzən mənanı itirə bilər, ehtiyatla istifadə etmək lazımdır.

            question_embedding_result = genai.embed_content(
                model=self.embedding_model,
                content=question,
                task_type="RETRIEVAL_QUERY"
            )
            question_embedding = question_embedding_result['embedding']

            # 2. Relevant hissələri tap (Retrieval)
            # FAISS 2D massiv tələb edir, ona görə [question_embedding] istifadə olunur.
            distances, indices = self.index.search(np.array([question_embedding], dtype=np.float32), k=15)

            context = ""
            sources = set()
            for i in indices[0]:
                context += self.chunks_data['texts'][i] + "\n\n"
                sources.add(self.chunks_data['metadata'][i]['source'])

            # 3. Cavab generasiya et (Generation)
            prompt = f"""
            Sən Azərbaycan Respublikasının Əmək Məcəlləsi üzrə hüquqi köməkçisən.
            Sənin vəzifən yalnız və yalnız aşağıda verilmiş 'Kontekst'ə əsaslanaraq istifadəçinin 'Sual'ını dəqiq və aydın şəkildə cavablandırmaqdır.
            Əgər cavab kontekstdə yoxdursa, heç bir əlavə məlumat vermədən sadəcə "Verilmiş məlumatlar əsasında bu suala dəqiq cavab verə bilmirəm." de.
            Cavabını bitirdikdən sonra, istifadə etdiyin məlumatın mənbəyini "Mənbə:" başlığı altında göstər.

            ---
            Kontekst:
            {context}
            ---
            Sual: {question}
            ---
            Cavab:
            """

            response = self.llm.generate_content(prompt)
            # Xətanın qarşısını almaq üçün cavabın olub-olmadığını yoxlayırıq
            if response.parts:
                answer = response.text
            else:
                # Əgər hələ də cavab yoxdursa, bu barədə məlumat veririk
                finish_reason = response.candidates[0].finish_reason if response.candidates else "Bilinmir"
                return f"Model cavab generasiya edə bilmədi. Səbəb: {finish_reason}. Zəhmət olmasa, təhlükəsizlik ayarlarınızı yoxlayın."

            if sources:
                answer += f"\n\nMənbə: {', '.join(sorted(list(sources)))}"

            return answer

        except Exception as e:
            return f"Cavab hazırlanarkən bir xəta baş verdi: {e}"


# --- Skriptin işə salınması üçün əsas blok ---
if __name__ == '__main__':
    # QASystem obyektini yaradırıq
    qa_bot = QASystem()

    print("\n--- Əmək Məcəlləsi QA Bot ---")
    print("Çıxmaq üçün 'exit' və ya 'çıx' yazın.")

    # İstifadəçi ilə interaktiv dialoq
    while True:
        user_question = input("\nSualınızı daxil edin: ")
        if user_question.lower() in ['exit', 'çıx']:
            print("Görüşənədək!")
            break

        # Sualı emal edib cavabı çap edirik
        print("\nCavab hazırlanır...")
        answer = qa_bot.answer_question(user_question)
        print("=" * 20 + " CAVAB " + "=" * 20)
        print(answer)
        print("=" * 47)