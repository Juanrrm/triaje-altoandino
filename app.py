import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy import signal

st.set_page_config(page_title="Triaje Altoandino", page_icon="🫀", layout="wide")

# --- FUNCIONES CLÍNICAS Y DE SEÑALES ---
def filtrar_ecg(senal_cruda, fs=125):

    """Aplica filtros digitales (Notch 60Hz y Pasa-bajas) al ECG."""
    # 1. Filtro Notch para eliminar el ruido de la red eléctrica de 60Hz
    w0 = 60.0 / (fs / 2)
    b_notch, a_notch = signal.iirnotch(w0, 30.0)
    senal_sin_60hz = signal.filtfilt(b_notch, a_notch, senal_cruda)
    
    # 2. Filtro Pasa-bajas (Butterworth de 4to orden) para eliminar ruido de alta frecuencia
    b_low, a_low = signal.butter(4, 40.0 / (fs / 2), 'low')
    return signal.filtfilt(b_low, a_low, senal_sin_60hz)

def interpretar_spo2(spo2_promedio, altitud):
    """Evalúa si la saturación es normal según la altitud de la posta."""
    if altitud < 1500:
        limite_normal = 95
    elif altitud < 3000:
        limite_normal = 92
    else:
        limite_normal = 88  # Percentil adaptado para hipoxia hipobárica crónica

    if spo2_promedio >= limite_normal:
        return "Normal para la altitud seleccionada", "success"
    else:
        return "Alerta: Hipoxia o desaturación crítica", "error"

# --- INTERFAZ PRINCIPAL ---
st.title("Sistema de Triaje Cardiopulmonar Altoandino 🏔️")

# Panel lateral para configuración de la posta
with st.sidebar:
    st.header("⚙️ Configuración del Contexto")
    altitud_posta = st.slider("Altitud del Puesto de Salud (msnm):", min_value=0, max_value=5000, value=3500, step=100)
    st.info(f"El sistema ajustará las alertas fisiológicas para **{altitud_posta} msnm**.")

archivo_subido = st.file_uploader("Arrastra aquí tu archivo de datos (.csv)", type=["csv"])

if archivo_subido is not None:
    try:
        datos = pd.read_csv(archivo_subido)
        columnas = datos.columns.tolist()
        
        st.markdown("---")
        
        # Dividir la pantalla en dos columnas para mejor visualización
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🩸 Oximetría de Pulso")
            columna_spo2 = st.selectbox("Selecciona la columna de SpO2:", columnas, index=columnas.index('SpO2') if 'SpO2' in columnas else 0)
            
            spo2_real = int(datos[columna_spo2].mean())
            mensaje_clinico, tipo_alerta = interpretar_spo2(spo2_real, altitud_posta)
            
            st.metric(label="SpO2 Promedio (Valor Crudo)", value=f"{spo2_real} %")
            
            if tipo_alerta == "success":
                st.success(f"🟢 Contexto Clínico: {mensaje_clinico}")
            else:
                st.error(f"🔴 Contexto Clínico: {mensaje_clinico}")
                
            st.caption("Nota: El sistema evalúa el valor real reportado por el sensor sin maquillar el dato, adaptando el umbral de alerta según la tolerancia fisiológica a la altitud.")
                
        with col2:
            st.subheader("🫀 Procesamiento de Actividad Eléctrica (ECG)")
            columna_ecg = st.selectbox("Selecciona la columna de ECG:", columnas, index=columnas.index('ECG_Raw') if 'ECG_Raw' in columnas else 0)
            
            vector_crudo = datos[columna_ecg].dropna().values
            vector_limpio = filtrar_ecg(vector_crudo)
            
            # Gráfico comparativo interactivo (limitado a 5 segundos / 625 muestras)
            fig = px.line(title="Comparación Analítica: Señal Cruda vs Filtrada")
            fig.add_scatter(y=vector_crudo[:625], name="Señal Cruda (Con Ruido)", opacity=0.35, line=dict(color='gray'))
            fig.add_scatter(y=vector_limpio[:625], name="Señal Filtrada (Limpia)", line=dict(color='#ff4b4b', width=2))
            fig.update_layout(xaxis_title="Muestras (fs = 125 Hz)", yaxis_title="Amplitud")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Bloque técnico explicativo para la sustentación
            with st.expander("🔍 Detalles de los filtros aplicados "):
                st.markdown("""
                **Filtros Digitales Implementados en la Tubería (Pipeline):**
                1. **Filtro Notch IIR (60 Hz):** Diseñado con un factor de calidad $Q = 30$ para remover la interferencia de la línea eléctrica sin atenuar los complejos QRS adyacentes.
                2. **Filtro Pasa-Bajas Butterworth (4to Orden):** Frecuencia de corte configurada a $40\text{ Hz}$ para eliminar ruido muscular (electromiográfico) y picos de alta frecuencia.
                3. **Fase Cero (filtfilt):** Se utiliza filtrado bidireccional para asegurar que el desfase sea exactamente cero, manteniendo la alineación temporal de las ondas P, QRS y T.
                """)

    except Exception as e:
        st.error(f"Hubo un error en el análisis: {e}")
else:
    st.info("Esperando a que subas un archivo .csv extraído de la tarjeta MicroSD...")