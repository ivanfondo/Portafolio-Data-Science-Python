import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="Sistema de Recomendación", layout="wide")

# --- FUNCIÓN PARA TARJETAS DE MÉTRICAS ---
def tarjeta_metrica(titulo, valor, color="#378ADD"):
    """Genera una tarjeta estilizada con sombreado para una métrica."""
    return f"""
    <div style="
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 5px solid {color};
        text-align: center;
        margin-bottom: 10px;
    ">
        <div style="font-size: 14px; color: #666; margin-bottom: 8px;">{titulo}</div>
        <div style="font-size: 32px; font-weight: 700; color: {color};">{valor}</div>
    </div>
    """

st.title("Sistema de Recomendación Híbrido")

# Creamos las dos pestañas
tab1, tab2 = st.tabs(["Análisis de co-compra (Apriori)", "Rendimiento del sistema"])

# --- PESTAÑA 1: GRAFO DE APRIORI ---
with tab1:
    st.header("Red de co-compra de productos")
    st.write(
        "Cada nodo es un producto y cada conexión indica que se compran juntos "
        "con frecuencia. Los colores representan clústeres de productos afines."
    )

    # Leemos el HTML del grafo que generamos con pyvis
    with open("grafo_cocompra_v2.html", "r", encoding="utf-8") as f:
        html_grafo = f.read()

    # Lo embebemos en el dashboard
    components.html(html_grafo, height=650, scrolling=True)

# --- PESTAÑA 2: RENDIMIENTO DEL SISTEMA ---
with tab2:
    st.header("RENDIMIENTO Y MONITORIZACIÓN SISTEMAS DE RECOMENDACIÓN")
    # --- Descripción de las métricas ---
    st.markdown("""
    <div style="
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 5px solid #000000;
        margin-bottom: 15px;
    ">
        <p style="margin: 0 0 10px 0; color: #333;">
            <strong style="color: #000000;">Precision@10</strong>: de los 10 productos
            recomendados, qué proporción acabó comprando el cliente. Mide la puntería
            de las recomendaciones.
        </p>
        <p style="margin: 0; color: #333;">
            <strong style="color: #000000;">Recall@10</strong>: de todo lo que el cliente
            compró, qué proporción cubrieron las recomendaciones. Mide la cobertura.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Datos ya calculados (de la evaluación en el notebook)
    metricas = {
        "Popularidad": {"precision": 0.125, "recall": 0.091},
        "ALS optimizado": {"precision": 0.239, "recall": 0.179},
    }
    n_evaluables = 998
    n_cold_start = 85

    # --- Fila de métricas principales ---
    st.subheader("Métricas de los modelos")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(tarjeta_metrica("Precision ALS", f"{metricas['ALS optimizado']['precision']:.3f}", "#378ADD"),
                    unsafe_allow_html=True)
    with col2:
        st.markdown(tarjeta_metrica("Recall ALS", f"{metricas['ALS optimizado']['recall']:.3f}", "#378ADD"),
                    unsafe_allow_html=True)
    with col3:
        st.markdown(tarjeta_metrica("Precision Popularidad", f"{metricas['Popularidad']['precision']:.3f}", "#1D9E75"),
                    unsafe_allow_html=True)
    with col4:
        st.markdown(tarjeta_metrica("Recall Popularidad", f"{metricas['Popularidad']['recall']:.3f}", "#1D9E75"),
                    unsafe_allow_html=True)

    # --- Reparto de clientes ---
    st.subheader("Distribución de clientes por modelo")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(tarjeta_metrica("Clientes con historial (ALS)", n_evaluables, "#E90E0E"),
                    unsafe_allow_html=True)
    with col_b:
        st.markdown(tarjeta_metrica("Clientes cold start (Popularidad)", n_cold_start, "#EF9F27"),
                    unsafe_allow_html=True)
        
        
    st.subheader("Comparación de modelos")

    modelos = ["ALS optimizado", "Popularidad"]
    precision = [metricas["ALS optimizado"]["precision"], metricas["Popularidad"]["precision"]]
    recall = [metricas["ALS optimizado"]["recall"], metricas["Popularidad"]["recall"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Precision", x=modelos, y=precision, marker_color="#378ADD"))
    fig.add_trace(go.Bar(name="Recall", x=modelos, y=recall, marker_color="#1D9E75"))

    fig.update_layout(
        barmode="group",
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


# PERSONALIZACIÓN DE DASHBOARD
st.markdown("""
<style>
    /* Contenedor de las pestañas - sin fondo */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        padding: 4px 0;
    }

    /* Cada pestaña individual */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #ffffff;
        border-radius: 10px;
        padding: 0 28px;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Pestaña activa - con degradado */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #378ADD 0%, #7F77DD 100%);
        color: #ffffff !important;
        box-shadow: 0 3px 10px rgba(55,138,221,0.4);
    }

    /* Quitar la línea/subrayado inferior por defecto */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent;
    }

    /* Fondo general de la app */
    .stApp {
        background-color: #eaf2fb;
    }
</style>
""", unsafe_allow_html=True)



