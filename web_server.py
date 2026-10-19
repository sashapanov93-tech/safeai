"""HTTP-сервер для Render: вебхук Telegram и health-check для мониторинга.

Стандартный ``Application.run_webhook`` поднимает tornado только с маршрутом
вебхука, поэтому любой GET-запрос (в том числе от UptimeRobot) получает 405 и
монитор считает бота упавшим. Здесь тот же tornado-сервер, но с маршрутами
``/telegram`` (апдейты Telegram), ``/health`` (мониторинг) и ``/`` (заглушка
для браузера).

Используется только публичный API python-telegram-bot: приложение поднимается
без ``Updater``, а разбор очереди апдейтов делает сам ``Application.start()``.
"""

import asyncio
import json
import logging
import os
import signal
from http import HTTPStatus

import tornado.httpserver
import tornado.web
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

DEFAULT_URL_PATH = "telegram"
DEFAULT_HEALTH_PATH = "/health"
DEFAULT_HEALTH_BODY = {"status": "ok", "service": "safeai", "role": "telegram-bot"}
ROOT_BODY = "SafeAI bot is running\n"


class HealthHandler(tornado.web.RequestHandler):
    """Отдаёт 200 OK: пинг монитора не даёт free-инстансу Render заснуть."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    async def get(self) -> None:
        self.set_status(HTTPStatus.OK)
        self.finish(json.dumps(DEFAULT_HEALTH_BODY))

    async def head(self) -> None:
        # UptimeRobot по умолчанию проверяет статус методом HEAD.
        self.set_status(HTTPStatus.OK)
        self.finish()


class RootHandler(tornado.web.RequestHandler):
    """Человекочитаемый ответ в корне вместо стандартной 404 от tornado."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "text/plain; charset=utf-8")

    async def get(self) -> None:
        self.set_status(HTTPStatus.OK)
        self.finish(ROOT_BODY)

    async def head(self) -> None:
        self.set_status(HTTPStatus.OK)
        self.finish()


class WebhookHandler(tornado.web.RequestHandler):
    """Принимает апдейты Telegram и складывает их в очередь приложения."""

    SUPPORTED_METHODS = ("POST",)

    def initialize(self, ptb_app: Application, secret_token: str | None = None) -> None:
        # pylint: disable=attribute-defined-outside-init
        self.ptb_application = ptb_app
        self.secret_token = secret_token

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    def _fail(self, status: HTTPStatus, reason: str) -> None:
        self.set_status(status)
        self.finish(json.dumps({"ok": False, "error": reason}))

    async def post(self) -> None:
        if self.secret_token:
            received = self.request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if received != self.secret_token:
                logger.warning("Запрос вебхука с неверным secret token")
                self._fail(HTTPStatus.FORBIDDEN, "wrong secret token")
                return

        try:
            payload = json.loads(self.request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Запрос вебхука без корректного JSON")
            self._fail(HTTPStatus.BAD_REQUEST, "update could not be processed")
            return

        try:
            update = Update.de_json(payload, self.ptb_application.bot)
        except Exception as exc:  # noqa: BLE001 — фиксируем любой мусор от Telegram
            logger.critical(
                "Не разобрали апдейт от Telegram, он не будет обработан: %r", payload,
                exc_info=exc,
            )
            self._fail(HTTPStatus.BAD_REQUEST, "update could not be processed")
            return

        # Дальше апдейт забирает Application._update_fetcher и зовёт process_update.
        await self.ptb_application.update_queue.put(update)
        self.set_status(HTTPStatus.OK)
        self.finish(json.dumps({"ok": True}))


def _build_http_app(
    application: Application,
    url_path: str,
    health_path: str,
    secret_token: str | None
) -> tornado.web.Application:
    webhook_path = rf"/{url_path.strip('/')}/?"
    return tornado.web.Application(
        [
            (webhook_path, WebhookHandler, {
                "ptb_app": application,
                "secret_token": secret_token
            }),
            (health_path, HealthHandler),
            (r"/", RootHandler)
        ]
    )


def _install_stop_handlers(stop_event: asyncio.Event) -> None:
    """Render останавливает контейнер SIGTERM — выходим аккуратно."""
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop_event.set())


async def serve_webhook(
    application: Application,
    port: int,
    webhook_url: str,
    url_path: str = DEFAULT_URL_PATH,
    health_path: str = DEFAULT_HEALTH_PATH,
    secret_token: str | None = None
) -> None:
    """Поднимает HTTP-сервер с вебхуком и health-check, работает до SIGTERM."""
    secret_token = secret_token or os.getenv("TELEGRAM_WEBHOOK_SECRET") or None

    await application.initialize()
    await application.start()

    try:
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as exc:  # noqa: BLE001 — без вебхука бот не получает апдейты
        logger.critical("Не удалось установить вебхук %s: %s", webhook_url, exc)
        await application.stop()
        await application.shutdown()
        raise

    logger.info("Вебхук Telegram установлен: %s", webhook_url)

    server = tornado.httpserver.HTTPServer(
        _build_http_app(application, url_path, health_path, secret_token)
    )
    server.listen(port, address="0.0.0.0")
    logger.info(
        "HTTP-сервер слушает 0.0.0.0:%s (вебхук %s, health %s)",
        port, f"/{url_path.strip('/')}", health_path
    )

    stop_event = asyncio.Event()
    _install_stop_handlers(stop_event)

    try:
        await stop_event.wait()
    finally:
        # Вебхук намеренно не удаляем: Telegram будет повторять доставку апдейтов,
        # пока Render поднимает следующий инстанс.
        logger.info("Останавливаем HTTP-сервер и приложение…")
        server.stop()
        await application.stop()
        await application.shutdown()
