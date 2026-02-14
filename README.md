# Smart Band Edge API Platform

Edge API Platform para dispositivo IoT ESP32 Smart Band que compone un sistema de monitoreo para frecuencias cardíacas en tiempo real.

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/docs/17/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Links

- **Swagger UI**: [https://smart-band-edge-api-platform.azurewebsites.net/docs](https://smart-band-edge-api-platform.azurewebsites.net/docs)
- **Status Page**: [https://stats.uptimerobot.com/MBVmW8Pm1L](https://stats.uptimerobot.com/MBVmW8Pm1L)

## User Stories

### US-01: Registrar Lectura de Frecuencia Cardíaca
**Como** usuario del dispositivo Smart Band  
**Quiero** enviar lecturas de frecuencia cardíaca 
**Para** que sean almacenadas y clasificadas automáticamente

**Criterios de aceptación:**
- El sistema acepta `smartBandId` (int) y `pulse` (string)
- Clasifica automáticamente según reglas de negocio:
  - **CRITICAL**: < 40 bpm
  - **LOW**: 40-59 bpm  
  - **NORMAL**: 60-140 bpm
  - **HIGH**: > 140 bpm
- Retorna el registro creado con ID único, timestamp y status
- Genera eventos de dominio: `HeartRateRecordedEvent` (siempre) y `AbnormalHeartRateDetectedEvent` (si status ≠ NORMAL)

**Endpoint:** `POST /api/v1/health-monitoring/data-records`

**Ejemplo de request desde ESP32:**
```json
{
  "smartBandId": 1,
  "pulse": "75"
}
```

---

### US-02: Consultar Historial de Lecturas
**Como** usuario del sistema  
**Quiero** consultar el historial de lecturas de un dispositivo  
**Para** visualizar el comportamiento de la frecuencia cardíaca en el tiempo

**Criterios de aceptación:**
- Retorna lecturas ordenadas por timestamp descendente
- Permite limitar la cantidad de resultados (default: 10)
- Incluye ID, pulse, status y timestamp de cada lectura

**Endpoint:** `GET /api/v1/health-monitoring/data-records/{smart_band_id}/history?limit=10`

---

### US-03: Obtener Estadísticas de Frecuencia Cardíaca
**Como** usuario del sistema  
**Quiero** ver estadísticas agregadas de un dispositivo  
**Para** analizar patrones y detectar anomalías

**Criterios de aceptación:**
- Retorna total de lecturas, promedio, mínimo y máximo
- Incluye conteo de lecturas anormales (LOW, HIGH, CRITICAL)
- Muestra distribución por status (NORMAL, LOW, HIGH, CRITICAL)

**Endpoint:** `GET /api/v1/health-monitoring/data-records/{smart_band_id}/statistics`

---

## Configuración ESP32

**Smart Band ID:** 1  
**Intervalo de medición:** 500ms  
**Umbral LED (alerta):** < 60 bpm o > 140 bpm  
**Cálculo de HR:** `(voltage / 3.3) * 675`
