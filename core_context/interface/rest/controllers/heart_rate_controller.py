from datetime import datetime, UTC
from sqlalchemy import text
from fastapi import Depends, HTTPException, FastAPI, Request
from core_context.application.internal.commandservices.record_heart_rate_command_handler import \
    RecordHeartRateCommandHandler
from core_context.application.internal.queryservices.heart_rate_query_handler import HeartRateQueryHandler
from core_context.domain.model.commands.record_heart_rate_command import RecordHeartRateCommand
from core_context.domain.model.queries.get_heart_rate_history_query import GetHeartRateHistoryQuery
from core_context.domain.model.queries.get_heart_rate_statistics_query import GetHeartRateStatisticsQuery
from core_context.interface.rest.dependencies.dependency_injection import get_query_handler, Dependencies, \
    get_command_handler
from core_context.interface.rest.dtos.heart_rate_history_item_dto import HeartRateHistoryItemDTO
from core_context.interface.rest.dtos.heart_rate_history_response_dto import HeartRateHistoryResponseDTO
from core_context.interface.rest.dtos.record_heart_rate_request_dto import RecordHeartRateRequestDTO
from core_context.interface.rest.dtos.record_heart_rate_response_dto import RecordHeartRateResponseDTO
from core_context.interface.rest.dtos.statistics_response_dto import StatisticsResponseDTO


def create_app(lifespan=None) -> FastAPI:
    """
    Factory function to create FastAPI application.
    Allows injection of lifespan context for startup/shutdown events.
    """
    app = FastAPI(
        title="Smart Band Edge Service",
        description="IoT Edge Api Platform for ESP32 Smart Band",
        version="1.0.0",
        lifespan=lifespan
    )

    # Health Check (simple - sin BD)
    @app.get("/health", tags=["Health Monitoring"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "smart-band-edge-service",
            "timestamp": datetime.now(UTC).isoformat()
        }

    # Keep-Alive endpoint - MANTIENE SUPABASE ACTIVO
    @app.api_route("/keepalive", methods=["GET", "HEAD"], tags=["Maintenance"], include_in_schema=False)
    async def keepalive(request: Request):
        """
        Keep-alive endpoint para evitar que Supabase pause el proyecto.
        Soporta tanto GET como HEAD (usado por UptimeRobot).

        Este endpoint hace una query simple a la base de datos para mantenerla activa.
        Configurar un monitor externo (UptimeRobot) para llamar este endpoint cada 5-10 minutos.
        """
        from shared_context.infrastructure.persistence.configuration.database_configuration import get_db_session

        # Si es HEAD, solo devolver headers sin body
        if request.method == "HEAD":
            return {"status": "alive"}

        # Si es GET, hacer query a la base de datos
        try:
            async for session in get_db_session():
                # Ejecutar query simple para mantener la conexión activa
                result = await session.execute(text("SELECT 1"))
                db_status = result.scalar()

                return {
                    "status": "alive",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "database": "connected" if db_status == 1 else "disconnected",
                    "message": "Keep-alive ping successful"
                }
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "error",
                "message": str(e)
            }

    # Ping simple para verificar que la API responde
    @app.api_route("/ping", methods=["GET", "HEAD"], tags=["Maintenance"], include_in_schema=False)
    async def ping(request: Request):
        """
        Simple ping endpoint sin interacción con base de datos.
        Útil para verificar que la API está respondiendo.
        Soporta GET y HEAD.
        """
        if request.method == "HEAD":
            return {"status": "pong"}

        return {
            "status": "pong",
            "timestamp": datetime.now(UTC).isoformat()
        }

    # Command Endpoint - Record Heart Rate
    @app.post(
        "/api/v1/health-monitoring/data-records",
        response_model=RecordHeartRateResponseDTO,
        status_code=201,
        tags=["Health Monitoring"]
    )
    async def record_heart_rate(
            request: RecordHeartRateRequestDTO,
            handler: RecordHeartRateCommandHandler = Depends(get_command_handler)
    ):
        """
        Record heart rate data from ESP32 smart band.
        Implements CQRS Command pattern.
        """
        try:
            # Convert DTO to Command
            command = RecordHeartRateCommand(
                smart_band_id=request.smartBandId,
                pulse=int(request.pulse)
            )

            # Execute command
            reading_id = await handler.handle(command)

            # Retrieve created entity for response
            repository = Dependencies.get_repository()
            reading = await repository.find_by_id(reading_id)

            if not reading:
                raise HTTPException(status_code=500, detail="Failed to retrieve created reading")

            return RecordHeartRateResponseDTO(
                id=reading.id,
                smart_band_id=reading.smart_band_id,
                pulse=reading.pulse,
                status=reading.status,
                timestamp=reading.timestamp,
                message=f"Heart rate recorded successfully. Status: {reading.status.value}"
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    # Query Endpoint - Get History
    @app.get(
        "/api/v1/health-monitoring/data-records/{smart_band_id}/history",
        response_model=HeartRateHistoryResponseDTO,
        tags=["Health Monitoring"]
    )
    async def get_heart_rate_history(
            smart_band_id: int,
            limit: int = 10,
            handler: HeartRateQueryHandler = Depends(get_query_handler)
    ):
        """
        Get heart rate history for a smart band.
        Implements CQRS Query pattern.
        """
        query = GetHeartRateHistoryQuery(smart_band_id=smart_band_id, limit=limit)
        readings = await handler.get_history(query)

        return HeartRateHistoryResponseDTO(
            smart_band_id=smart_band_id,
            readings=[
                HeartRateHistoryItemDTO(
                    id=r.id,
                    pulse=r.pulse,
                    status=r.status,
                    timestamp=r.timestamp
                )
                for r in readings
            ],
            total=len(readings)
        )

    # Query Endpoint - Get Statistics
    @app.get(
        "/api/v1/health-monitoring/data-records/{smart_band_id}/statistics",
        response_model=StatisticsResponseDTO,
        tags=["Health Monitoring"]
    )
    async def get_heart_rate_statistics(
            smart_band_id: int,
            handler: HeartRateQueryHandler = Depends(get_query_handler)
    ):
        """
        Get heart rate statistics for a smart band.
        Implements CQRS Query pattern.
        """
        query = GetHeartRateStatisticsQuery(smart_band_id=smart_band_id)
        stats = await handler.get_statistics(query)

        return StatisticsResponseDTO(**stats)

    # Error Handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(exc):
        return {
            "error": "Validation Error",
            "detail": str(exc)
        }

    return app


# Default instance for backward compatibility
app = create_app()