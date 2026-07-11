import streamlit as st
import pandas as pd
import joblib
import shap
import numpy as np
import altair as alt

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 1. Configuración de página
st.set_page_config(page_title="Churn Dashboard", layout="wide")

st.markdown("""
    <style>
    .main-header {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 8px solid #007BFF;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
        text-align: center;
    }
    .kpi-label {
        color: #666666;
        font-size: 14px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .kpi-value {
        color: #1E1E1E;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Función auxiliar: asigna acción según probabilidad y cortes ---
def asignar_accion(prob, umbral, alpha):
    if prob < umbral:
        return "No actuar"
    elif prob < alpha:
        return "Email"
    else:
        return "Llamada"

COLOR_ACCION = {
    "No actuar": "#95A5A6",
    "Email":     "#F39C12",
    "Llamada":   "#E74C3C"
}

# --- Inicializacion del estado de sesion (registro de contactados y notas) ---
# 'contactados' es un conjunto de IDs ya trabajados.
# 'notas' es un diccionario {id_cliente: texto de impresiones}.
if 'contactados' not in st.session_state:
    st.session_state.contactados = set()
if 'notas' not in st.session_state:
    st.session_state.notas = {}

@st.cache_resource
def load_assets():
    try:
        assets = joblib.load(DATA_DIR / "modelo_churn_final.pkl")
        model = assets['model']
        features = assets['features']
        df_modelo = pd.read_csv(DATA_DIR / "datos_test_dashboard.csv", index_col=0)
        df_visual = pd.read_csv(DATA_DIR / "TelcoChurn.csv", index_col=0)
        explainer = shap.TreeExplainer(model)
        return model, df_modelo, df_visual, explainer, features
    except Exception as e:
        st.error(f"Error cargando archivos: {e}")
        return None, None, None, None, None
    
model, df, df_perfil, explainer, features = load_assets()

if model is not None:
    # 3. Sidebar - Panel de Control
    st.sidebar.title("🔍 Panel de Control")

    # Probabilidades base
    probabilidades = model.predict_proba(df[features])[:, 1]
    df['Probabilidad'] = probabilidades

    # --- CONFIGURACIÓN DE ESTRATEGIA (dos cortes) ---
    st.sidebar.subheader("⚙️ Configuración de Estrategia")
    umbral = st.sidebar.slider(
        "Umbral de actuación (%)", 0, 100, 50,
        help="Por debajo de este valor no se realiza ninguna acción."
    ) / 100
    alpha = st.sidebar.slider(
        "Frontera Email / Llamada (%)", 0, 100, 68,
        help="Entre el umbral y este valor se envía Email; por encima, Llamada."
    ) / 100
    if alpha < umbral:
        alpha = umbral

    df['Accion'] = df['Probabilidad'].apply(lambda p: asignar_accion(p, umbral, alpha))

    # --- RESUMEN DE ACCIONES EN TIEMPO REAL ---
    st.sidebar.divider()
    st.sidebar.subheader("📋 Acciones recomendadas")
    conteo = df['Accion'].value_counts()
    col_a, col_b, col_c = st.sidebar.columns(3)
    col_a.metric("📵 Nada", int(conteo.get("No actuar", 0)))
    col_b.metric("✉️ Email", int(conteo.get("Email", 0)))
    col_c.metric("📞 Llamada", int(conteo.get("Llamada", 0)))
    st.sidebar.divider()

    # --- GESTION DE CONTACTOS: PENDIENTES vs CONTACTADOS ---
    st.sidebar.subheader("📇 Gestión de Contactos")

    # Progreso
    total_clientes = len(df)
    n_contactados = len(st.session_state.contactados)
    st.sidebar.progress(n_contactados / total_clientes if total_clientes else 0,
                        text=f"{n_contactados} / {total_clientes} contactados")

    # Modo de trabajo: pendientes o consultar contactados
    modo = st.sidebar.radio("Ver:", ["Pendientes", "Contactados"])

    if modo == "Pendientes":
        # Lista de no contactados (opcional: filtrar por accion)
        filtro = st.sidebar.selectbox(
            "Filtrar por acción:",
            ["Todas", "Llamada", "Email", "No actuar"]
        )
        df_pendientes = df[~df.index.isin(st.session_state.contactados)]
        if filtro != "Todas":
            df_pendientes = df_pendientes[df_pendientes['Accion'] == filtro]

        # Ordenamos por probabilidad descendente (mas urgentes primero)
        df_pendientes = df_pendientes.sort_values('Probabilidad', ascending=False)

        if len(df_pendientes) == 0:
            st.sidebar.success("✅ No quedan clientes pendientes con este filtro.")
            id_cliente = None
        else:
            id_cliente = st.sidebar.selectbox(
                "Cliente a contactar:", df_pendientes.index
            )
    else:
        # Modo consulta de contactados
        contactados_lista = sorted(st.session_state.contactados)
        if len(contactados_lista) == 0:
            st.sidebar.info("Aún no hay clientes contactados.")
            id_cliente = None
        else:
            id_cliente = st.sidebar.selectbox(
                "Cliente contactado (consulta):", contactados_lista
            )

    # 4. Visualización Principal
    if id_cliente:
        ya_contactado = id_cliente in st.session_state.contactados

        st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)
        estado_txt = " ✅ (Contactado)" if ya_contactado else ""
        st.markdown(f'<div class="main-header"><h2 style="margin:0; color:white;">Análisis Detallado Cliente: {id_cliente}{estado_txt}</h2></div>', unsafe_allow_html=True)

        datos_cliente = df.loc[[id_cliente]]
        prob = datos_cliente['Probabilidad'].values[0]
        accion_cliente = datos_cliente['Accion'].values[0]

        # KPIs (5 tarjetas)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            color_resaltado = "#FF4B4B" if prob >= umbral else "#28A745"
            st.markdown(f'<div class="kpi-card" style="border-left-color: {color_resaltado};"><div class="kpi-label">Riesgo fuga</div><div class="kpi-value">{prob:.1%}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Gasto Mensual</div><div class="kpi-value">{datos_cliente["MonthlyCharges"].values[0]:.2f} €</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card" style="border-left-color: #F39C12;"><div class="kpi-label">Antigüedad (meses) </div><div class="kpi-value">{int(datos_cliente["tenure"].values[0])}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="kpi-card" style="border-left-color: #691769;"><div class="kpi-label">Gasto Total</div><div class="kpi-value">{datos_cliente["TotalCharges"].values[0]:.2f} €</div></div>', unsafe_allow_html=True)
        with c5:
            color_accion = COLOR_ACCION.get(accion_cliente, "#007BFF")
            st.markdown(f'<div class="kpi-card" style="border-left-color: {color_accion};"><div class="kpi-label">Acción recomendada</div><div class="kpi-value" style="color:{color_accion};">{accion_cliente}</div></div>', unsafe_allow_html=True)

        st.divider()

        # 5. ZONA MIXTA
        col_grafico, col_perfil = st.columns([2, 1])

        with col_grafico:
            st.subheader("⛓️ Factores de Riesgo")

            # Calculamos los valores SHAP del cliente (solo los numeros, sin matplotlib)
            shap_values = explainer.shap_values(datos_cliente[features])
            valores_reales = datos_cliente[features].iloc[0]

            # DataFrame con la contribucion de cada variable
            df_shap = pd.DataFrame({
                'Factor': features,
                'Impacto': shap_values[0],
                'Valor': valores_reales.values
            })
            df_shap['abs_impacto'] = df_shap['Impacto'].abs()
            df_shap = df_shap.sort_values('abs_impacto', ascending=False)
            df_shap['Etiqueta'] = df_shap.apply(
                lambda r: f"{r['Factor']} ({r['Valor']})", axis=1
            )
            df_shap['Sentido'] = df_shap['Impacto'].apply(
                lambda x: 'Aumenta el riesgo' if x > 0 else 'Reduce el riesgo'
            )

            # Grafico de barras horizontal con Altair (nativo, sin matplotlib)
            chart = alt.Chart(df_shap).mark_bar().encode(
                x=alt.X('Impacto:Q', title='Impacto en el riesgo de fuga'),
                y=alt.Y('Etiqueta:N', sort='-x', title=None),
                color=alt.Color(
                    'Sentido:N',
                    scale=alt.Scale(
                        domain=['Aumenta el riesgo', 'Reduce el riesgo'],
                        range=['#E74C3C', '#3498DB']
                    ),
                    legend=alt.Legend(title=None, orient='top')
                ),
                tooltip=['Factor', 'Valor', 'Impacto']
            ).properties(height=350)

            st.altair_chart(chart, width='stretch')

            st.markdown('<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 13px;">ℹ️ <b>Interpretación:</b> Las barras <span style="color:#E74C3C">rojas</span> aumentan el riesgo de fuga, las <span style="color:#3498DB">azules</span> lo disminuyen. La longitud indica la magnitud del efecto.</div>', unsafe_allow_html=True)

        with col_perfil:
            st.subheader("👤 Perfil del Cliente")
            columnas_no_interes = ['Churn', 'Dependents', 'Partner', 'gender', 'Probabilidad', 'Accion']
            cols_a_mostrar = [c for c in df_perfil.columns if c not in columnas_no_interes]
            perfil_completo = df_perfil.loc[[id_cliente], cols_a_mostrar].T
            perfil_completo.columns = ['Valor']
            perfil_completo['Valor'] = perfil_completo['Valor'].apply(
                lambda x: "Sí" if x == 1 else ("No" if x == 0 else x)
            )
            # Forzamos toda la columna a texto para evitar tipos mezclados
            # (str + float) que rompen la serializacion a Arrow de Streamlit.
            perfil_completo['Valor'] = perfil_completo['Valor'].astype(str)
            st.dataframe(perfil_completo, width='stretch', height=450)

        st.divider()

        # 6. GESTION DEL CONTACTO: notas + marcar como contactado
        st.subheader("📝 Registro de contacto")

        # Cada cliente tiene su propio campo de notas mediante una key unica.
        # Al cambiar de cliente, Streamlit muestra automaticamente el widget
        # correspondiente: vacio si es nuevo, o con su nota si ya existe.
        key_nota = f"nota_{id_cliente}"

        # Inicializamos el contenido del widget la primera vez que se ve este
        # cliente, tomando la nota ya guardada (si la hubiera).
        if key_nota not in st.session_state:
            st.session_state[key_nota] = st.session_state.notas.get(id_cliente, "")

        st.text_area(
            "Impresiones del contacto (para próximas aproximaciones):",
            key=key_nota,
            placeholder="Ej.: Cliente molesto con la velocidad de la fibra. Ofrecer mejora de tarifa en próxima llamada.",
            height=100
        )

        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if not ya_contactado:
                if st.button("✅ Marcar como contactado", type="primary"):
                    # Guardamos la nota actual y marcamos como contactado
                    texto = st.session_state[key_nota].strip()
                    if texto:
                        st.session_state.notas[id_cliente] = texto
                    st.session_state.contactados.add(id_cliente)
                    st.rerun()
            else:
                if st.button("↩️ Reabrir (marcar como pendiente)"):
                    st.session_state.contactados.discard(id_cliente)
                    st.rerun()
        with col_btn2:
            if st.button("💾 Guardar notas"):
                texto = st.session_state[key_nota].strip()
                if texto:
                    st.session_state.notas[id_cliente] = texto
                    st.success("Notas guardadas.")
                else:
                    st.info("No hay texto que guardar.")

else:
    st.error("No se pudo inicializar la aplicación. Verifica los archivos.")