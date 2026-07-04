import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy import signal
from datetime import datetime, timedelta

# Configuración inicial de la página
st.set_page_config(page_title="Triaje Altoandino", page_icon="🫀", layout="wide")

# --- INICIALIZACIÓN DE LA MEMORIA DE SESIÓN ---
# Estas variables recordarán si el doctor ya entró y simularán el tiempo
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'offset_minutos' not in st.session_state:
    st.session_state.offset_minutos = 0

# --- LÓGICA DE BIOSEGURIDAD Y TIEMPO DINÁMICO ---
hora_actual_real = datetime.now()
# Sumamos los minutos artificiales para el modo demo
hora_simulada = hora_actual_real + timedelta(minutes=st.session_state.offset_minutos)

# Dividir el tiempo en bloques fijos de 15 minutos (ej. 16:00, 16:15, 16:30)
minuto_bloque = (hora_simulada.minute // 15) * 15
hora_bloque = hora_simulada.replace(minute=minuto_bloque, second=0, microsecond=0)

# El token cambiará automáticamente si se pasa al siguiente bloque de 15 min
token_dinamico = f"ALT-{hora_bloque.strftime('%H%M')}"
CLAVE_MAESTRA = "BIO-2026"

# --- FUNCIONES CLÍNICAS Y DE SEÑALES ---
def filtrar_ecg(senal_cruda, fs=125):
    w0 = 60.0 / (fs / 2)
    b_notch, a_notch = signal.iirnotch(w0, 30.0)
    senal_sin_60hz = signal.filtfilt(b_notch, a_notch, senal_cruda)
    b_low, a_low = signal.butter(4, 40.0 / (fs / 2), 'low')
    return signal.filtfilt(b_low, a_low, senal_sin_60hz)

def interpretar_spo2(spo2_promedio, altitud):
    if altitud < 1500: limite_normal = 95
    elif altitud < 3000: limite_normal = 92
    else: limite_normal = 88 
    
    if spo2_promedio >= limite_normal:
        return "Normal para la altitud seleccionada", "success"
    else:
        return "Alerta: Hipoxia o desaturación crítica", "error"


# --- PANEL LATERAL: MODO DEMO PARA EL PROFESOR ---
with st.sidebar:
    st.header("👨‍🏫 Panel de Sustentación")
    st.info("Este panel demuestra la bioseguridad. En la vida real, el técnico no ve esto, el token se lo dicta el especialista.")
    
    st.write(f"**Reloj del Sistema:** {hora_simulada.strftime('%H:%M')}")
    st.write(f"**Token de este bloque:** `{token_dinamico}`")
    
    if st.button("⏳ Simular paso del tiempo (+15 min)"):
        st.session_state.offset_minutos += 15
        st.rerun() # Recarga la página para generar el nuevo token
        
    st.markdown("---")
    st.write(f"**Clave Maestra (No expira):** `{CLAVE_MAESTRA}`")
    st.markdown("---")
    
    # Controles de altitud (solo visibles si está autenticado para no saturar)
    if st.session_state.autenticado:
        st.header("⚙️ Configuración del Contexto")
        altitud_posta = st.slider("Altitud del Puesto de Salud (msnm):", 0, 5000, 3500, 100)


# --- INTERFAZ PRINCIPAL ---
st.title("Sistema de Triaje Cardiopulmonar Altoandino 🏔️")

# SISTEMA DE PUERTA (COMPROBACIÓN DE BIOSEGURIDAD)
if not st.session_state.autenticado:
    st.warning("🔒 **Acceso Restringido:** Por normas de bioseguridad, ingrese el token temporal provisto por el especialista.")
    
    col_auth1, col_auth2 = st.columns([1, 2])
    with col_auth1:
        token_ingresado = st.text_input("Token de Acceso:", type="password")
        if st.button("Desbloquear Sistema"):
            # Si acierta el token temporal o la clave maestra, entra y se queda en memoria
            if token_ingresado == token_dinamico or token_ingresado == CLAVE_MAESTRA:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Acceso Denegado: El token es incorrecto o ha expirado.")
else:
    # --- ENTORNO SEGURO Y PERMANENTE ---
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        st.success("✅ **Entorno Seguro:** Sesión médica iniciada con éxito. Tiempo de análisis ilimitado.")
    with col_top2:
        if st.button("Cerrar Sesión y Bloquear"):
            st.session_state.autenticado = False
            st.rerun()

    archivo_subido = st.file_uploader("Arrastra aquí el archivo de la HealthyPi 5 (.csv)", type=["csv"])

    if archivo_subido is not None:
        try:
            datos = pd.read_csv(archivo_subido)
            columnas = datos.columns.tolist()
            st.markdown("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("🩸 Oximetría de Pulso")
                columna_spo2 = st.selectbox("Selecciona la columna de SpO2:", columnas, index=columnas.index('SpO2') if 'SpO2' in columnas else 0)
                spo2_real = int(datos[columna_spo2].mean())
                mensaje_clinico, tipo_alerta = interpretar_spo2(spo2_real, altitud_posta)
                
                st.metric(label="SpO2 Promedio (Valor Crudo)", value=f"{spo2_real} %")
                if tipo_alerta == "success": st.success(f"🟢 Contexto Clínico: {mensaje_clinico}")
                else: st.error(f"🔴 Contexto Clínico: {mensaje_clinico}")
                    
            with col2:
                st.subheader("🫀 Procesamiento (ECG)")
                columna_ecg = st.selectbox("Selecciona la columna de ECG:", columnas, index=columnas.index('ECG_Raw') if 'ECG_Raw' in columnas else 0)
                
                vector_crudo = datos[columna_ecg].dropna().values
                vector_limpio = filtrar_ecg(vector_crudo)
                
                fig = px.line(title="Comparación: Señal Cruda vs Filtrada")
                fig.add_scatter(y=vector_crudo[:625], name="Señal Cruda", opacity=0.35, line=dict(color='gray'))
                fig.add_scatter(y=vector_limpio[:625], name="Señal Filtrada", line=dict(color='#ff4b4b', width=2))
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error al analizar el archivo: {e}")