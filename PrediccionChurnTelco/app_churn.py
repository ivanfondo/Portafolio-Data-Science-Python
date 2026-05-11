import streamlit as st
import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt

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

# 2. Carga de Assets
@st.cache_resource
def load_assets():
    try:
        assets = joblib.load('modelo_churn_final.pkl')
        model = assets['model']
        features = assets['features'] 
        df_modelo = pd.read_csv('datos_test_dashboard.csv', index_col=0) 
        df_visual = pd.read_csv('TelcoChurn.csv', index_col=0) 
        explainer = shap.TreeExplainer(model)
        return model, df_modelo, df_visual, explainer, features
    except Exception as e:
        st.error(f"Error cargando archivos: {e}")
        return None, None, None, None, None

model, df, df_perfil, explainer, features = load_assets()

if model is not None:
    # 3. Sidebar
    st.sidebar.title("🔍 Panel de Control")

    # Calculamos probabilidades
    probabilidades = model.predict_proba(df[features])[:, 1]
    df['Probabilidad'] = probabilidades

    # Filtro simplificado
    tipo_cliente = st.sidebar.radio("Ver clientes:", ["Todos", "Riesgo Alto (>50%)", "Riesgo Bajo (<50%)"])

    if tipo_cliente == "Riesgo Alto (>50%)":
        df_mostrar = df[df['Probabilidad'] >= 0.5]
    elif tipo_cliente == "Riesgo Bajo (<50%)":
        df_mostrar = df[df['Probabilidad'] < 0.5]
    else:
        df_mostrar = df

    id_cliente = st.sidebar.selectbox("Selecciona ID de Cliente:", df_mostrar.index)

    # --- TOP 10 EN SIDEBAR ---
    st.sidebar.divider()
    st.sidebar.subheader("🔝 Top 10 Riesgo Crítico")
    top_10 = df.sort_values(by='Probabilidad', ascending=False).head(10)
    top_10_display = top_10[['Probabilidad']].copy()
    top_10_display['Probabilidad'] = top_10_display['Probabilidad'].map('{:.1%}'.format)
    st.sidebar.table(top_10_display)

    # 4. Visualización Principal
    if id_cliente:
        st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="main-header"><h2 style="margin:0; color:white;">Análisis Detallado Cliente: {id_cliente}</h2></div>', unsafe_allow_html=True)

        datos_cliente = df.loc[[id_cliente]]
        prob = datos_cliente['Probabilidad'].values[0]

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            color_resaltado = "#FF4B4B" if prob >= 0.6 else "#28A745"
            st.markdown(f'<div class="kpi-card" style="border-left-color: {color_resaltado};"><div class="kpi-label">Riesgo fuga</div><div class="kpi-value">{prob:.1%}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Gasto Mensual</div><div class="kpi-value">{datos_cliente["MonthlyCharges"].values[0]:.2f} €</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card" style="border-left-color: #F39C12;"><div class="kpi-label">Antigüedad (meses) </div><div class="kpi-value">{int(datos_cliente["tenure"].values[0])}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="kpi-card" style="border-left-color: #691769;"><div class="kpi-label">Gasto Total</div><div class="kpi-value">{datos_cliente["TotalCharges"].values[0]:.2f} €</div></div>', unsafe_allow_html=True)

        st.divider()

        # 5. ZONA MIXTA
        col_grafico, col_perfil = st.columns([2, 1]) 

        with col_grafico:
            st.subheader("⛓️ Factores de Riesgo")
            plt.switch_backend('Agg')
            fig = plt.figure(figsize=(12, 3), dpi=120)

            # Obtener SHAP values y los valores reales del cliente
            shap_values = explainer.shap_values(datos_cliente[features])
            valores_reales = datos_cliente[features].iloc[0]

            shap.force_plot(
                explainer.expected_value, 
                shap_values[0], 
                features=valores_reales, # Añade los valores reales al gráfico
                feature_names=features,
                matplotlib=True, 
                show=False,
                contribution_threshold=0.05,
                text_rotation=90
            )
            plt.subplots_adjust(top=1)
            st.pyplot(plt.gcf(), use_container_width=True, clear_figure=True)
            plt.close(fig)

            st.markdown('<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 13px;">ℹ️ <b>Interpretación:</b> Las barras <span style="color:red">rojas</span> aumentan el riesgo, las <span style="color:blue">azules</span> lo disminuyen.</div>', unsafe_allow_html=True)

        with col_perfil:
            st.subheader("👤 Perfil del Cliente")
            columnas_no_interes = ['Churn', 'Dependents', 'Partner', 'gender']
            cols_a_mostrar = [c for c in df_perfil.columns if c not in columnas_no_interes]

            perfil_completo = df_perfil.loc[[id_cliente], cols_a_mostrar].T
            perfil_completo.columns = ['Valor']

            perfil_completo['Valor'] = perfil_completo['Valor'].apply(
                lambda x: "Sí" if x == 1 else ("No" if x == 0 else x)
            )
            st.dataframe(perfil_completo, use_container_width=True, height=450)
else:
    st.error("No se pudo inicializar la aplicación. Verifica los archivos.")
