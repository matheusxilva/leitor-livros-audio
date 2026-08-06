import streamlit as st
import pypdf
import asyncio
import edge_tts
import google.generativeai as genai
import tempfile
import os

# Configuração da página
st.set_page_config(page_title="Leitor de Livros", page_icon="🎧", layout="centered")
st.title("🎧 Ouvir Livro por Capítulos")
st.caption("Gere o áudio por trechos para ser muito mais rápido e não travar!")

# Barra lateral
with st.sidebar:
    st.header("Configurações")
    gemini_key = st.text_input("Sua chave de API do Gemini:", type="password")
    
    opcoes_vozes = {
        "pt-BR-FranciscaNeural": "🇧🇷 Francisca (Feminina)",
        "pt-BR-AntonioNeural": "🇧🇷 Antonio (Masculino)",
        "pt-BR-ThalitaNeural": "🇧🇷 Thalita (Feminina)",
        "pt-PT-DuarteNeural": "🇵🇹 Duarte (Portugal - Masculino)",
        "pt-PT-RaquelNeural": "🇵🇹 Raquel (Portugal - Feminina)"
    }
    
    voice_option = st.selectbox(
        "Escolha a voz:",
        options=list(opcoes_vozes.keys()),
        format_func=lambda x: opcoes_vozes[x]
    )

def extract_text_from_pdf(pdf_file, start_page, end_page):
    reader = pypdf.PdfReader(pdf_file)
    text = ""
    total_pages = len(reader.pages)
    start = max(0, start_page - 1)
    end = min(total_pages, end_page)
    for i in range(start, end):
        extracted = reader.pages[i].extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def clean_text_with_gemini(raw_text, api_key):
    genai.configure(api_key=api_key)
    
    # Busca a lista de modelos disponíveis
    modelo_escolhido = None
    modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Força o aplicativo a escolher os modelos Flash mais novos e com maior limite gratuito
    for nome in modelos_disponiveis:
        if 'flash' in nome and ('3.6' in nome or '3.5' in nome):
            modelo_escolhido = nome
            break
            
    # Se não achar nenhum com 3, pega o último da lista (geralmente o mais recente)
    if not modelo_escolhido and modelos_disponiveis:
        modelo_escolhido = modelos_disponiveis[-1]
        
    if not modelo_escolhido:
        raise Exception("Nenhum modelo de texto compatível encontrado para esta chave.")
        
    model = genai.GenerativeModel(modelo_escolhido)
    
    # ⚠️ A MÁGICA: DESLIGANDO OS FILTROS DE SEGURANÇA
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    
    prompt = (
        "Você é um assistente que prepara textos para narração em áudio. "
        "Remova cabeçalhos, rodapés e números de página do texto abaixo. "
        "Junte frases quebradas. Entregue APENAS o texto limpo, sem adicionar comentários.\n\n"
        f"Texto:\n{raw_text}"
    )
    
    response = model.generate_content(prompt, safety_settings=safety_settings)
    return response.text

async def generate_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

uploaded_file = st.file_uploader("Envie o PDF do seu livro:", type=["pdf"])

if uploaded_file:
    reader_temp = pypdf.PdfReader(uploaded_file)
    total_pages = len(reader_temp.pages)
    st.info(f"📚 Este livro tem **{total_pages} páginas** no total.")
    
    col1, col2 = st.columns(2)
    with col1:
        start_page = st.number_input("Página Inicial:", min_value=1, max_value=total_pages, value=1)
    with col2:
        end_page = st.number_input("Página Final:", min_value=1, max_value=total_pages, value=min(10, total_pages))
        
    st.caption("💡 *Dica: Recomendamos gerar blocos de 10 a 20 páginas por vez (ex: um capítulo).*")

    if gemini_key:
        if st.button("🚀 Converter Trecho em Áudio", use_container_width=True):
            with st.spinner(f"1/3 Extraindo texto das páginas {start_page} a {end_page}..."):
                raw_text = extract_text_from_pdf(uploaded_file, start_page, end_page)
                
            with st.spinner("2/3 Gemini limpando o texto (Filtros desativados)..."):
                try:
                    cleaned_text = clean_text_with_gemini(raw_text, gemini_key)
                    st.success("✨ Texto limpo pelo Gemini com sucesso!")
                except Exception as e:
                    # Agora, se der erro, ele vai te fofocar exatamente o que o servidor do Google recusou
                    st.error(f"🚨 Erro exato do Gemini: {e}")
                    st.warning("Gerando áudio com o texto original bruto...")
                    cleaned_text = raw_text 

            with st.spinner("3/3 Gravando a narração neural..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    audio_path = tmp_file.name
                
                asyncio.run(generate_audio(cleaned_text, voice_option, audio_path))
                
                st.success("🎉 Áudio gerado com sucesso!")
                st.audio(audio_path, format="audio/mp3")
                
                with open(audio_path, "rb") as file:
                    st.download_button(
                        label=f"⬇️ Baixar Áudio (Páginas {start_page} a {end_page})",
                        data=file,
                        file_name=f"Livro_Paginas_{start_page}_a_{end_page}.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
    else:
        st.warning("Insira sua chave do Gemini na barra lateral para continuar.")
