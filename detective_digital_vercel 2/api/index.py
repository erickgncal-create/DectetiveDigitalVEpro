import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Incluir ruta local para módulos
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from detective_core import (
    DetectiveDigitalEngine,
    TipoMaterial,
    TipoViolacion,
    EstadoEpistemologico,
    NivelCorroboracion,
    TipoDialogo,
    QueryBuilderAnexoV,
    AutomatedSourceMonitor,
    GazetteScraperProcessor
)

app = FastAPI(
    title="Detective Digital OSINT API",
    description="Backend Serverless para Detective Digital en Vercel",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# En entornos serverless como Vercel, usamos /tmp para almacenamiento temporal de la sesión
engine = DetectiveDigitalEngine(workspace_path="/tmp/detective_workspace")
monitor_manager = AutomatedSourceMonitor(engine)
gazette_processor = GazetteScraperProcessor(engine)

# ==========================================
# MODELOS PYDANTIC
# ==========================================
class CrearEventoRequest(BaseModel):
    titulo: str
    tipo_violacion: TipoViolacion
    latitud: float
    longitud: float
    toponimo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    entidades_iniciales: Optional[List[str]] = None

class CrearMonitorRequest(BaseModel):
    nombre: str
    plataforma: str
    palabras_clave: List[str]
    frase_exacta: Optional[str] = None
    excluir_terminos: Optional[List[str]] = None
    usuario_from: Optional[str] = None
    usuario_to: Optional[str] = None
    solo_imagenes: bool = False
    solo_videos: bool = False
    cerca_de: Optional[str] = None
    objetivo_ddhh: str
    frecuencia_segundos: int = 300

class IngestaTextoRequest(BaseModel):
    texto: str
    url_origen: str
    plataforma: str
    autor_perfil: str
    investigador_id: str
    ip_recoleccion: str
    identidad_virtual: Optional[str] = None
    tipo_material: TipoMaterial = TipoMaterial.PUBLICACION_REDES
    fecha_publicacion: Optional[datetime] = None
    evento_id: Optional[str] = None

# ==========================================
# RUTAS DE LA API
# ==========================================
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "plataforma": "Vercel Serverless",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/monitores")
def crear_monitor(req: CrearMonitorRequest):
    query_x = QueryBuilderAnexoV.construir_query_x(
        palabras_clave=req.palabras_clave,
        frase_exacta=req.frase_exacta,
        excluir_terminos=req.excluir_terminos,
        usuario_from=req.usuario_from,
        usuario_to=req.usuario_to,
        solo_imagenes=req.solo_imagenes,
        solo_videos=req.solo_videos,
        cerca_de=req.cerca_de
    )
    regla = monitor_manager.registrar_monitor(
        nombre=req.nombre,
        plataforma=req.plataforma,
        consulta_sintactica=query_x,
        objetivo_ddhh=req.objetivo_ddhh,
        frecuencia_segundos=req.frecuencia_segundos
    )
    return {
        "mensaje": "Monitor booleano configurado",
        "monitor": {
            "id": regla.id,
            "nombre": regla.nombre,
            "consulta_booleana": regla.consulta_sintactica
        }
    }

@app.get("/api/monitores")
def listar_monitores():
    return {
        "total": len(monitor_manager.monitores),
        "monitores": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "plataforma": m.plataforma,
                "consulta": m.consulta_sintactica,
                "activo": m.activo
            } for m in monitor_manager.monitores.values()
        ]
    }

@app.post("/api/eventos")
def crear_evento(req: CrearEventoRequest):
    evento = engine.crear_evento_base(
        titulo=req.titulo,
        tipo_violacion=req.tipo_violacion,
        latitud=req.latitud,
        longitud=req.longitud,
        toponimo=req.toponimo,
        fecha_inicio=req.fecha_inicio,
        fecha_fin=req.fecha_fin,
        entidades_iniciales=req.entidades_iniciales
    )
    return {"mensaje": "Evento creado", "evento_id": evento.id}

@app.get("/api/eventos")
def listar_eventos():
    return {
        "eventos": [
            {
                "id": ev.id,
                "titulo": ev.titulo,
                "tipo_violacion": ev.tipo_violacion.value,
                "ubicacion": ev.geolocalizacion.toponimo,
                "estado": ev.estado.value,
                "nivel_corroboracion": ev.nivel_corroboracion.value,
                "entidades": ev.entidades_involucradas
            } for ev in engine.eventos.values()
        ]
    }

@app.get("/api/matriz")
def obtener_matriz():
    return {
        "total_dialogos": len(engine.matriz_dialogos),
        "dialogos": [
            {
                "id": d.id,
                "tipo_dialogo": d.tipo_dialogo.value,
                "score": d.score_confianza,
                "justificacion": d.justificacion,
                "alerta_contradiccion": d.contradiccion_detectada
            } for d in engine.matriz_dialogos
        ]
    }
