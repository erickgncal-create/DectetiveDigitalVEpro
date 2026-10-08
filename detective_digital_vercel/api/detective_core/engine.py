import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

from .models import (
    FuenteDigital,
    EventoIncidente,
    CoincidenciaDialogo,
    TipoMaterial,
    TipoViolacion,
    CoordenadaGeografica,
    VentanaTemporal,
    EstadoEpistemologico,
    NivelCorroboracion
)
from .custody import CustodyManager
from .extractor import ForensicEntityExtractor
from .matcher import MatrixCorrelationEngine


class DetectiveDigitalEngine:
    def __init__(self, workspace_path: str = "./detective_workspace"):
        self.workspace = Path(workspace_path)
        self.custody_mgr = CustodyManager(str(self.workspace / "storage"))
        self.matcher = MatrixCorrelationEngine()

        self.fuentes: Dict[str, FuenteDigital] = {}
        self.eventos: Dict[str, EventoIncidente] = {}
        self.matriz_dialogos: List[CoincidenciaDialogo] = []

    def crear_evento_base(
        self,
        titulo: str,
        tipo_violacion: TipoViolacion,
        latitud: float,
        longitud: float,
        toponimo: str,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        entidades_iniciales: Optional[List[str]] = None,
    ) -> EventoIncidente:
        evento_id = f"ev_{uuid.uuid4().hex[:8]}"
        evento = EventoIncidente(
            id=evento_id,
            titulo=titulo,
            tipo_violacion=tipo_violacion,
            geolocalizacion=CoordenadaGeografica(
                latitud=latitud,
                longitud=longitud,
                toponimo=toponimo
            ),
            temporalidad=VentanaTemporal(inicio=fecha_inicio, fin=fecha_fin),
            entidades_involucradas=entidades_iniciales or []
        )
        self.eventos[evento_id] = evento
        return evento

    def ingresar_evidencia(
        self,
        filename: str,
        content_bytes: bytes,
        url_origen: str,
        tipo_material: TipoMaterial,
        plataforma: str,
        autor_perfil: str,
        investigador_id: str,
        ip_recoleccion: str,
        identidad_virtual: Optional[str] = None,
        texto_contenido: str = "",
        fecha_publicacion_original: Optional[datetime] = None,
        evento_asociado_id: Optional[str] = None,
    ) -> Tuple[FuenteDigital, List[CoincidenciaDialogo]]:
        evidence_id = f"fnt_{uuid.uuid4().hex[:8]}"

        fuente = self.custody_mgr.preserve_evidence(
            evidence_id=evidence_id,
            filename=filename,
            content_bytes=content_bytes,
            url_origen=url_origen,
            tipo_material=tipo_material,
            plataforma=plataforma,
            autor_perfil=autor_perfil,
            investigador_id=investigador_id,
            ip_recoleccion=ip_recoleccion,
            identidad_virtual=identidad_virtual,
            texto_contenido=texto_contenido,
            fecha_publicacion_original=fecha_publicacion_original,
        )
        self.fuentes[evidence_id] = fuente

        entidades = ForensicEntityExtractor.extract_entities_from_text(texto_contenido)
        nombres_entidades = [e.nombre_canonico for e in entidades]

        if evento_asociado_id and evento_asociado_id in self.eventos:
            ev = self.eventos[evento_asociado_id]
            ev.fuentes_asociadas.append(evidence_id)
            for n in nombres_entidades:
                if n not in ev.entidades_involucradas:
                    ev.entidades_involucradas.append(n)
            self.matcher.recalculate_event_status(ev, len(ev.fuentes_asociadas))

        nuevos_dialogos: List[CoincidenciaDialogo] = []
        for ev in self.eventos.values():
            coincidencia = self.matcher.evaluate_dialogue(fuente, ev, self.fuentes)
            if coincidencia:
                nuevos_dialogos.append(coincidencia)
                self.matriz_dialogos.append(coincidencia)
                if evidence_id not in ev.fuentes_asociadas:
                    ev.fuentes_asociadas.append(evidence_id)
                for n in nombres_entidades:
                    if n not in ev.entidades_involucradas:
                        ev.entidades_involucradas.append(n)
                self.matcher.recalculate_event_status(ev, len(ev.fuentes_asociadas))

        return fuente, nuevos_dialogos

    def generar_reporte_matriz_dialogo(self) -> str:
        lines = [
            "# MATRIZ DE INTELIGENCIA Y DIÁLOGO OSINT",
            f"**Fecha de generación:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Total de Fuentes Preservadas:** {len(self.fuentes)}",
            f"**Eventos Bajo Investigación:** {len(self.eventos)}",
            f"**Conexiones / Diálogos Detectados:** {len(self.matriz_dialogos)}",
            "\n---\n"
        ]

        for ev in self.eventos.values():
            lines.append(f"## Evento: {ev.titulo}")
            lines.append(f"- **Tipo de Violación:** {ev.tipo_violacion.value}")
            lines.append(f"- **Ubicación:** {ev.geolocalizacion.toponimo} (Lat: {ev.geolocalizacion.latitud}, Lon: {ev.geolocalizacion.longitud})")
            lines.append(f"- **Estado Epistemológico:** `{ev.estado.value}` | **Nivel Corroboración:** `{ev.nivel_corroboracion.value}`")
            lines.append(f"- **Actores / Entidades Identificadas:** {', '.join(ev.entidades_involucradas) or 'Sin identificar'}")
            lines.append(f"- **Fuentes Vinculadas ({len(ev.fuentes_asociadas)}):**")
            for fid in ev.fuentes_asociadas:
                f = self.fuentes.get(fid)
                if f:
                    lines.append(f"  * `[{f.id}]` ({f.plataforma} - {f.tipo_material.value}) Hash: `{f.hash_sha256[:16]}...`")

            dialogos_evento = [d for d in self.matriz_dialogos if d.evento_id == ev.id]
            if dialogos_evento:
                lines.append("\n### 🔗 Cruce de Evidencias (Data en Diálogo):")
                for d in dialogos_evento:
                    fa = self.fuentes.get(d.fuente_a_id)
                    fb = self.fuentes.get(d.fuente_b_id)
                    lines.append(f"> **[{d.tipo_dialogo.value}]** (Confianza: {int(d.score_confianza*100)}%)")
                    lines.append(f"> *Diálogo entre:* `{fa.plataforma if fa else 'N/A'}` y `{fb.plataforma if fb else 'N/A'}`")
                    lines.append(f"> *Hallazgo:* {d.justificacion}")
                    if d.contradiccion_detectada:
                        lines.append(f"> ⚠️ **Alerta:** {d.contradiccion_detectada}")
                    lines.append("")
            lines.append("\n---\n")

        return "\n".join(lines)

    def exportar_ficha_anexo_iv(self, fuente_id: str) -> Dict[str, Any]:
        f = self.fuentes.get(fuente_id)
        if not f:
            raise ValueError(f"Fuente {fuente_id} no encontrada.")

        return {
            "1_INFORMACION_RECOLECTOR": {
                "persona_o_equipo": f.registro_custodia.investigador_id,
                "ip_recoleccion": f.registro_custodia.ip_recoleccion,
                "identidad_virtual_usada": f.registro_custodia.identidad_virtual_usada or "No utilizada",
                "sello_tiempo_utc": f.registro_custodia.sello_tiempo_utc,
            },
            "2_INFORMACION_OBJETIVO": {
                "url_origen": f.url_origen,
                "plataforma": f.plataforma,
                "autor_publicador": f.autor_perfil,
                "estado_contenido": f.estado_contenido,
                "texto_o_descripcion": f.texto_contenido,
            },
            "3_INTEGRIDAD_Y_PAQUETE_DATOS": {
                "identificador_fuente": f.id,
                "algoritmo_hash": "SHA-256 (FIPS 180-4)",
                "hash_sha256_copia_probatoria": f.hash_sha256,
                "ruta_almacenamiento_seguro": f.ruta_copia_probatoria,
                "ruta_copia_trabajo": f.ruta_copia_trabajo,
            },
            "4_SERVICIOS_Y_HERRAMIENTAS": {
                "software_utilizado": f.registro_custodia.herramientas_utilizadas,
                "repositorio_archivado": f.archivado_externo_url or "Pendiente de captura",
            }
        }
