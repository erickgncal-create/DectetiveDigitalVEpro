import math
import uuid
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from .models import (
    FuenteDigital,
    EventoIncidente,
    CoincidenciaDialogo,
    TipoDialogo,
    EstadoEpistemologico,
    NivelCorroboracion,
    CoordenadaGeografica,
    TipoEntidad
)
from .extractor import ForensicEntityExtractor


def haversine_distance_meters(coord1: CoordenadaGeografica, coord2: CoordenadaGeografica) -> float:
    R = 6371000.0
    phi1 = math.radians(coord1.latitud)
    phi2 = math.radians(coord2.latitud)
    delta_phi = math.radians(coord2.latitud - coord1.latitud)
    delta_lambda = math.radians(coord2.longitud - coord1.longitud)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class MatrixCorrelationEngine:
    def __init__(
        self,
        umbral_distancia_metros: float = 2500.0,
        umbral_tiempo_horas: float = 8.0,
    ):
        self.umbral_distancia_metros = umbral_distancia_metros
        self.umbral_tiempo_horas = umbral_tiempo_horas

    def evaluate_dialogue(
        self,
        nueva_fuente: FuenteDigital,
        evento: EventoIncidente,
        otras_fuentes: Dict[str, FuenteDigital]
    ) -> Optional[CoincidenciaDialogo]:
        entidades_nueva = ForensicEntityExtractor.extract_entities_from_text(nueva_fuente.texto_contenido)
        nombres_entidades_nueva = {e.nombre_canonico for e in entidades_nueva}

        coincide_tiempo = False
        delta_horas = 999999.0
        if nueva_fuente.fecha_publicacion_original and evento.temporalidad:
            delta_segundos = abs(
                (nueva_fuente.fecha_publicacion_original - evento.temporalidad.inicio).total_seconds()
            )
            delta_horas = delta_segundos / 3600.0
            coincide_tiempo = delta_horas <= self.umbral_tiempo_horas

        coincide_espacio = False
        distancia_m = 999999.0
        for ent in entidades_nueva:
            if ent.tipo == TipoEntidad.UBICACION and "lat" in ent.detalles:
                coord_nueva = CoordenadaGeografica(
                    latitud=ent.detalles["lat"],
                    longitud=ent.detalles["lon"],
                    toponimo=ent.nombre_canonico
                )
                distancia_m = haversine_distance_meters(coord_nueva, evento.geolocalizacion)
                if distancia_m <= self.umbral_distancia_metros:
                    coincide_espacio = True
                    break

        entidades_comunes = list(nombres_entidades_nueva.intersection(set(evento.entidades_involucradas)))
        perfil_nuevo = ForensicEntityExtractor.detect_rhetoric_profile(nueva_fuente.texto_contenido)
        
        for f_id in evento.fuentes_asociadas:
            if f_id not in otras_fuentes:
                continue
            fuente_previa = otras_fuentes[f_id]
            perfil_previo = ForensicEntityExtractor.detect_rhetoric_profile(fuente_previa.texto_contenido)

            # Caso 1: CONTRADICCIÓN NARRATIVA
            if (perfil_nuevo["perfil_probable"] == "OFICIAL" and perfil_previo["perfil_probable"] == "TESTIGO/TERRENO") or \
               (perfil_nuevo["perfil_probable"] == "TESTIGO/TERRENO" and perfil_previo["perfil_probable"] == "OFICIAL"):
                if coincide_espacio or coincide_tiempo or entidades_comunes:
                    justificacion = (
                        f"Tensión narrativa detectada: {nueva_fuente.plataforma} ({perfil_nuevo['perfil_probable']}) "
                        f"presenta términos {perfil_nuevo['coincidencias_oficiales'] or perfil_nuevo['coincidencias_terreno']} "
                        f"en contraste con {fuente_previa.plataforma} ({perfil_previo['perfil_probable']}) "
                        f"en torno a {evento.geolocalizacion.toponimo}."
                    )
                    return CoincidenciaDialogo(
                        id=f"dial_{uuid.uuid4().hex[:8]}",
                        evento_id=evento.id,
                        fuente_a_id=fuente_previa.id,
                        fuente_b_id=nueva_fuente.id,
                        tipo_dialogo=TipoDialogo.CONTRADICCION_OFICIAL_VS_HECHO,
                        score_confianza=0.92,
                        justificacion=justificacion,
                        entidades_comunes=entidades_comunes,
                        contradiccion_detectada="Discrepancia sustancial entre versión institucional y registro en terreno"
                    )

            # Caso 2: PRUEBA DE VINCULACIÓN
            if nueva_fuente.tipo_material == "DOCUMENTO_PDF" and ("gaceta" in nueva_fuente.plataforma.lower() or "resolucion" in nueva_fuente.texto_contenido.lower()):
                if entidades_comunes:
                    justificacion = (
                        f"Prueba de Vinculación (Berkeley §60): Documento oficial/gaceta vincula a la entidad "
                        f"{entidades_comunes} con facultades o presencia en el sector del incidente {evento.titulo}."
                    )
                    return CoincidenciaDialogo(
                        id=f"dial_{uuid.uuid4().hex[:8]}",
                        evento_id=evento.id,
                        fuente_a_id=fuente_previa.id,
                        fuente_b_id=nueva_fuente.id,
                        tipo_dialogo=TipoDialogo.PRUEBA_DE_VINCULACION,
                        score_confianza=0.88,
                        justificacion=justificacion,
                        entidades_comunes=entidades_comunes
                    )

            # Caso 3: CORROBORACIÓN CRUZADA
            if coincide_espacio and coincide_tiempo:
                justificacion = (
                    f"Corroboración espaciotemporal: Nueva pieza ({nueva_fuente.tipo_material}) coincide a "
                    f"{distancia_m:.1f}m y delta {delta_horas:.1f}h con evidencia previa {fuente_previa.id}."
                )
                return CoincidenciaDialogo(
                    id=f"dial_{uuid.uuid4().hex[:8]}",
                    evento_id=evento.id,
                    fuente_a_id=fuente_previa.id,
                    fuente_b_id=nueva_fuente.id,
                    tipo_dialogo=TipoDialogo.CORROBORACION_CRUZADA,
                    score_confianza=0.85,
                    justificacion=justificacion,
                    entidades_comunes=entidades_comunes
                )

        return None

    @staticmethod
    def recalculate_event_status(evento: EventoIncidente, total_fuentes: int) -> None:
        if total_fuentes >= 5:
            evento.nivel_corroboracion = NivelCorroboracion.ALTO
            evento.estado = EstadoEpistemologico.HECHO
        elif total_fuentes >= 3:
            evento.nivel_corroboracion = NivelCorroboracion.MEDIO
            evento.estado = EstadoEpistemologico.HECHO
        else:
            evento.nivel_corroboracion = NivelCorroboracion.BAJO
            evento.estado = EstadoEpistemologico.CONJETURA
