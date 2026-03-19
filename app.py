import streamlit as st
import pandas as pd
from main import LeadProcessor
import os

st.set_page_config(page_title="VYUD AI Agent", page_icon="🤖", layout="wide")

st.title("🤖 VYUD Sales Engagement")
st.markdown("Загрузите список сайтов, и AI-агент автоматически извлечет данные и напишет персонализированные письма.")

# Sidebar for controls
st.sidebar.header("Настройки")
max_workers = st.sidebar.slider("Параллельные потоки (Скорость)", 1, 10, 3)
api_key = st.sidebar.text_input("OpenAI API Key (Опционально)", type="password")

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

# Main area
urls_input = st.text_area("Введите URL сайтов (по одному в строке):", 
                          "https://www.hubspot.com/our-story\nhttps://www.salesforce.com/company/about-us/")

if st.button("🚀 Запустить магию (Run Batch)", type="primary"):
    urls = [u.strip() for u in urls_input.split('\n') if u.strip()]
    
    if not urls:
        st.warning("Пожалуйста, введите хотя бы один URL.")
    elif not os.getenv("OPENAI_API_KEY"):
        st.error("Пожалуйста, введите OpenAI API Key в настройках слева или убедитесь, что он есть в файле .env.")
    else:
        # Save to temp file
        with open("leads_ui.txt", "w") as f:
            f.write("\n".join(urls))
            
        st.info(f"Начинаю обработку {len(urls)} лидов...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # We need a slightly modified processor that yields progress
        processor = LeadProcessor(input_file="leads_ui.txt", output_file="results_ui.csv", max_workers=max_workers)
        
        # Clear previous results
        if os.path.exists("results_ui.csv"):
            os.remove("results_ui.csv")
            
        import csv
        with open("results_ui.csv", mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Company Name", "Industry", "Tech Stack", "CRM Detected", "Confidence Score", "Email Draft"])
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        processed = 0
        with ThreadPoolExecutor(max_workers=processor.max_workers) as executor:
            future_to_url = {executor.submit(processor.process_single_url, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    processor.save_result(result)
                except Exception as exc:
                    st.error(f"Ошибка при обработке {url}: {exc}")
                
                processed += 1
                progress_bar.progress(processed / len(urls))
                status_text.text(f"Обработано {processed} из {len(urls)}")
                
        st.success("✅ Обработка завершена!")
        
        # Display results
        if os.path.exists("results_ui.csv"):
            df = pd.read_csv("results_ui.csv")
            st.subheader("📊 Результаты")
            st.dataframe(df, use_container_width=True)
            
            # Download button
            with open("results_ui.csv", "rb") as file:
                btn = st.download_button(
                    label="📥 Скачать CSV",
                    data=file,
                    file_name="vyud_results.csv",
                    mime="text/csv"
                )
            
            # Email Tinder View
            st.subheader("💌 Предпросмотр писем (Tinder View)")
            for index, row in df.iterrows():
                with st.expander(f"Письмо для: {row['Company Name']} (Уверенность: {row['Confidence Score']})"):
                    st.markdown(f"**CRM:** {row['CRM Detected']} | **Стек:** {row['Tech Stack']}")
                    st.text_area("Текст письма", row['Email Draft'], height=300)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.button("✅ Approve", key=f"app_{index}", use_container_width=True)
                    with col2:
                        st.button("✏️ Edit", key=f"ed_{index}", use_container_width=True)
                    with col3:
                        st.button("❌ Reject", key=f"rej_{index}", use_container_width=True)
