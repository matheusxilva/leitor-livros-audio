import streamlit as st
import pypdf
import asyncio
import edge_tts
import google.generativeai as genai
import tempfile
import os

# Configuração da página para celular
st.set_page_config(
    page_title="Leitor de Livros",
    page_icon="🎧",
    layout="centered"
)

st.title("🎧 Ouvir Livro em Áudio")
st.caption("Transforme seus PDFs em áudios fluidos com IA")

# Barra lateral para configurar a API do Gemini
with st.sidebar:
    st.header("Configurações")
    gemini_key = st.text_input("Sua chave de API do Gemini:", type="password")
    
    # Dicionário com várias opções de vozes
    opcoes_vozes = {
        "pt-BR-FranciscaNeural": "🇧🇷 Francisca (Feminina)",
        "pt-BR-AntonioNeural": "🇧🇷 Antonio (Masculino)",
        "pt-BR-ThalitaNeural": "🇧🇷 Thalita (Feminina)",
        "pt-PT-DuarteNeural": "🇵🇹 Duarte (Portugal - Masculino)",
        "pt-PT-RaquelNeural": "🇵🇹 Raquel (Portugal - Feminina)",
        "en-US-AriaNeural": "🇺🇸 Aria (Inglês EUA - Feminina)",
        "en-US-GuyNeural": "🇺🇸 Guy (Inglês EUA - Masculino)"
    }
    
    # Seleção da voz (Edge-TTS)
    voice_option = st.selectbox(
        "Escolha a voz:",
        options=list(opcoes_vozes.keys()),
        format_func=lambda x: opcoes_vozes[x]
    )

# Função para extrair texto do PDF
def extract_text_from_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# Função para limpar o texto com o Gemini Pro
def clean_text_with_gemini(raw_text, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = (
        "Você é um assistente especializado em preparar textos de livros para narração em áudio. "
        "Abaixo está um trecho extraído de um PDF. Remova cabeçalhos, rodapés, números de página, "
        "índices, URLs e notas explicativas. Mantenha apenas a história/narrativa contínua do livro de forma fluida. "
        "Não adicione nenhuma introdução ou comentário seu, entregue apenas o texto limpo do livro em português.\n\n"
        f"Texto:\n{raw_text[:12000]}" # Limite seguro por lote
    )
    
    response = model.generate_content(prompt)
    return response.text

# Função assíncrona para gerar o áudio via Edge-TTS
async def generate_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# Upload do arquivo PDF
uploaded_file = st.file_uploader("Envie o PDF do seu livro:", type=["pdf"])

if uploaded_file and gemini_key:
    if st.button("🚀 Converter Livro em Áudio", use_container_width=True):
        with st.spinner("1/3 Extraindo texto do PDF..."):
            raw_text = extract_text_from_pdf(uploaded_file)
            
        with st.spinner("2/3 Gemini limpando cabeçalhos e números de páginas..."):
            try:
                cleaned_text = clean_text_with_gemini(raw_text, gemini_key)
            except Exception as e:
                st.error(f"Erro no Gemini: {e}")
                cleaned_text = raw_text # Fallback caso a chave falhe

        with st.spinner("3/3 Gerando narração em áudio neural..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                audio_path = tmp_file.name
            
            # Rodar a conversão assíncrona de áudio
            asyncio.run(generate_audio(cleaned_text, voice_option, audio_path))
            
            st.success("Áudio gerado com sucesso!")
            
            # Player de Áudio no celular
            st.audio(audio_path, format="audio/mp3")
            
            # Botão para baixar o MP3 e ouvir offline
            with open(audio_path, "rb") as file:
                st.download_button(
                    label="⬇️ Baixar MP3 para o iPhone",
                    data=file,
                    file_name=f"{uploaded_file.name.replace('.pdf', '')}_audio.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
elif uploaded_file and not gemini_key:
    st.warning("Insira sua chave do Gemini Pro na barra lateral para continuar.")
