import asyncio
from datetime import datetime, timezone

from app.repositories.sp_repository import sp_repo
from app.websocket.connection_manager import ws_manager


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemoExecutionManager:
    def __init__(self):
        self.tasks: dict[int, asyncio.Task] = {}
        self.cancel_events: dict[int, asyncio.Event] = {}

    def is_running(self, vehiculo_id: int) -> bool:
        task = self.tasks.get(vehiculo_id)
        return task is not None and not task.done()

    def start(self, vehiculo_id: int, demo_id: int) -> None:
        if self.is_running(vehiculo_id):
            raise RuntimeError("Ya existe una demo activa")
        event = asyncio.Event()
        self.cancel_events[vehiculo_id] = event
        task = asyncio.create_task(self.run_demo(vehiculo_id, demo_id, event))
        self.tasks[vehiculo_id] = task

    def cancel_demo(self, vehiculo_id: int) -> bool:
        event = self.cancel_events.get(vehiculo_id)
        if event is None or not self.is_running(vehiculo_id):
            return False
        event.set()
        return True

    async def _wait_or_cancel(self, event: asyncio.Event, milliseconds: int) -> bool:
        if milliseconds <= 0:
            return event.is_set()
        try:
            await asyncio.wait_for(event.wait(), timeout=milliseconds / 1000)
            return True
        except asyncio.TimeoutError:
            return False

    async def run_demo(self, vehiculo_id: int, demo_id: int, cancel_event: asyncio.Event):
        try:
            movimientos = await asyncio.to_thread(sp_repo.sp_obtener_movimientos_demo, demo_id)
            await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
                "evento": "DEMO_INICIO", "id_vehiculo": vehiculo_id, "id_demo": demo_id,
                "total_movimientos": len(movimientos), "timestamp": utc_now(),
            })
            for mov in movimientos:
                if cancel_event.is_set():
                    break
                await asyncio.to_thread(sp_repo.sp_actualizar_estado, vehiculo_id, mov["id_comando"], True)
                await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
                    "evento": "MOVIMIENTO_DEMO", "id_vehiculo": vehiculo_id,
                    "orden": mov["orden"], "comando": mov["comando"], "codigo": mov["codigo"],
                    "duracion_ms": mov["duracion_ms"], "pausa_ms": mov["pausa_ms"], "timestamp": utc_now(),
                })
                if await self._wait_or_cancel(cancel_event, mov["duracion_ms"]):
                    break
                if await self._wait_or_cancel(cancel_event, mov["pausa_ms"]):
                    break
            evento = "DEMO_CANCELADA" if cancel_event.is_set() else "DEMO_FINALIZADA"
            await ws_manager.broadcast_to_vehiculo(vehiculo_id, {
                "evento": evento, "id_vehiculo": vehiculo_id, "id_demo": demo_id, "timestamp": utc_now(),
            })
        finally:
            self.tasks.pop(vehiculo_id, None)
            self.cancel_events.pop(vehiculo_id, None)


demo_runner = DemoExecutionManager()

