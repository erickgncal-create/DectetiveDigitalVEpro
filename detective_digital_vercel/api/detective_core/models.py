from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class TipoMaterial(str, Enum):
    IMAGEN = "IMAGEN"
    VIDEO = "VIDEO"
    DOCUMENTO_PDF = "DOCUMENTO_PDF"
    PUBLICACION_REDES = "PUBLICACION_REDES"
    PAGINA_WEB = "PAGINA_WEB"
    OTRO = "OTRO"


class TipoEntidad(str, Enum):
    PERSONA = "PERSONA"
    ORGANISMO_SEGURIDAD = "ORGANISMO_SEGURIDAD"
    EMPRESA = "EMPRESA"
    VEHICULO = "VEHICULO"
    ARMAMENTO = "ARMAMENTO"
    UBICACION = "UBICACION"
    SIMBOLO = "SIMBOLO"


class TipoViolacion(str, Enum):
    DETENCION_ARBITRARIA = "DETENCION_ARBITRARIA"
    DESAPARICION_FORZADA = "DESAPARICION_FORZADA"
    EJECUCION_EXTRAJUDICIAL = "EJECUCION_EXTRAJUDICIAL"
    USO_EXCESIVO_FUERZA = "USO_EXCESIVO_FUERZA"
    ALLANAMIENTO_ILEGAL = "ALLANAMIENTO_ILEGAL"
    CENSURA_BLOQUEO = "CENSURA_BLOQUEO"
    CORRUPCION_PODER = "CORRUPCION_PODER"
    NO_DETERMINADA = "NO_DETERMINADA"


class EstadoEpistemologico(str, Enum):
    HECHO = "HECHO"
    CONJETURA = "CONJETURA"
    INCOGNITA = "INCOGNITA"


class NivelCorroboracion(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class TipoDialogo(str, Enum):
    CORROBORACION_CRUZADA = "CORROBORACION_CRUZADA"
    CONTRADICCION_OFICIAL_VS_HECHO = "CONTRADICCION_OFICIAL_VS_HECHO"
    PRUEBA_DE_VINCULACION = "PRUEBA_DE_VINCULACION"
    PATRON_ESTRUCTURAL = "PATRON_ESTRUCTURAL"
    COINCIDENCIA_CONTEXTUAL = "COINCIDENCIA_CONTEXTUAL"


@dataclass
class CoordenadaGeografica:
    latitud: float
    longitud: float
    toponimo: str
    radio_incertidumbre_metros: float = 100.0


@dataclass
class VentanaTemporal:
    inicio: datetime
    fin: datetime
    metodo_cronolocalizacion: str = "TEXTO_CONTENIDO"


@dataclass
class RegistroCustodia:
    investigador_id: str
    ip_recoleccion: str
    identidad_virtual_usada: Optional[str]
    sello_tiempo_utc: str
    herramientas_utilizadas: List[str]
    hash_sha256_probatorio: str


@dataclass
class FuenteDigital:
    id: str
    url_origen: str
    tipo_material: TipoMaterial
    plataforma: str
    autor_perfil: str
    hash_sha256: str
    ruta_copia_probatoria: str
    ruta_copia_trabajo: str
    registro_custodia: RegistroCustodia
    fecha_publicacion_original: Optional[datetime] = None
    texto_contenido: str = ""
    metadatos_exif: Dict[str, Any] = field(default_factory=dict)
    codigo_fuente_html: Optional[str] = None
    archivado_externo_url: Optional[str] = None
    estado_contenido: str = "DISPONIBLE"


@dataclass
class Entidad:
    id: str
    tipo: TipoEntidad
    nombre_canonico: str
    alias: List[str] = field(default_factory=list)
    detalles: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventoIncidente:
    id: str
    titulo: str
    tipo_violacion: TipoViolacion
    geolocalizacion: CoordenadaGeografica
    temporalidad: VentanaTemporal
    estado: EstadoEpistemologico = EstadoEpistemologico.CONJETURA
    nivel_corroboracion: NivelCorroboracion = NivelCorroboracion.BAJO
    fuentes_asociadas: List[str] = field(default_factory=list)
    entidades_involucradas: List[str] = field(default_factory=list)
    narrativas: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CoincidenciaDialogo:
    id: str
    evento_id: str
    fuente_a_id: str
    fuente_b_id: str
    tipo_dialogo: TipoDialogo
    score_confianza: float
    justificacion: str
    entidades_comunes: List[str]
    contradiccion_detectada: Optional[str] = None
    timestamp_deteccion: str = field(default_factory=lambda: datetime.utcnow().isoformat())
