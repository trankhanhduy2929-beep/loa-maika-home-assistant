"""Cloud API client reverse engineered from MAIKA Android 3.2.3."""

from __future__ import annotations

import asyncio
import base64
import codecs
import json
import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import aiohttp

from .const import (
    APP_DEVICE_TYPE,
    APP_LANGUAGE,
    APP_TIMEZONE,
    APP_VERSION,
    CHATBOT_BASE_URL,
    DEVICE_INFO_FIELDS,
    REST_UPDATE_FIELDS,
    USERS_BASE_URL,
)
from .phone import is_email_login_identifier, normalize_login_identifier

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
STREAM_TIMEOUT = aiohttp.ClientTimeout(
    total=None,
    connect=30,
    sock_connect=30,
    sock_read=180,
)

_FRAME_START = "$START_JSON"
_FRAME_END = "$END_JSON"
_MAX_STREAM_BUFFER = 1024 * 1024
_STREAM_WRAPPER_KEYS = ("directive", "event", "message", "response", "data")


class MaikaApiError(Exception):
    """Base MAIKA API error."""


class MaikaAuthenticationError(MaikaApiError):
    """Authentication failed."""


class MaikaConnectionError(MaikaApiError):
    """Communication with the MAIKA cloud failed."""


class MaikaApiClient:
    """Asynchronous MAIKA cloud client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        phone_number: str,
        password: str,
        client_id: str,
        session_id: str,
    ) -> None:
        self._session = session
        self._login_identifier = normalize_login_identifier(phone_number)
        self._password = password
        self._client_id = client_id
        self._session_id = session_id

        self._access_token: str | None = None
        self._user_id: int | None = None
        self._token_valid_until = 0.0
        self._auth_lock = asyncio.Lock()

        self._connected = asyncio.Event()
        self._listener_generation = 0
        self._stopping = False
        self._listener_task: asyncio.Task[Any] | None = None
        self._event_callback: Callable[[dict[str, Any]], None] | None = None
        self._device_info_waiters: dict[str, list[asyncio.Future[dict[str, Any]]]] = {}
        self.live_device_info: dict[str, dict[str, Any]] = {}
        self._voice_cache: list[dict[str, Any]] | None = None

    @property
    def user_id(self) -> int | None:
        """Return the authenticated MAIKA user ID."""
        return self._user_id

    @property
    def listener_connected(self) -> bool:
        """Return whether the cloud event stream is connected."""
        return self._connected.is_set()

    @property
    def listener_generation(self) -> int:
        """Return a counter incremented for every successful stream handshake."""
        return self._listener_generation

    def set_event_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for decoded cloud stream events."""
        self._event_callback = callback

    def set_listener_task(self, task: asyncio.Task[Any]) -> None:
        """Store the Home Assistant-managed listener task."""
        self._listener_task = task

    async def async_login(self) -> dict[str, Any]:
        """Authenticate using the same endpoint as the Android app."""
        if is_email_login_identifier(self._login_identifier):
            login_path = "/v1/auth/login"
            login_payload = {
                "device_id": self._client_id,
                "email": self._login_identifier,
                "password": self._password,
            }
        else:
            login_path = "/v1/auth/otp/login"
            login_payload = {
                "phone_number": self._login_identifier,
                "password": self._password,
            }
        try:
            async with self._session.post(
                f"{USERS_BASE_URL}{login_path}",
                json=login_payload,
                headers=self._rest_headers(include_authorization=False),
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    await response.read()
                    raise MaikaAuthenticationError("Invalid MAIKA credentials")
                if response.status >= 400:
                    await response.read()
                    raise MaikaConnectionError(
                        f"MAIKA login returned HTTP {response.status}"
                    )
                payload = await self._read_json(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MaikaConnectionError("Unable to connect to MAIKA login") from err

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict) or not data.get("access_token"):
            raise MaikaAuthenticationError("MAIKA login did not return a token")

        self._access_token = str(data["access_token"])
        try:
            self._user_id = int(data["id"])
        except (KeyError, TypeError, ValueError) as err:
            raise MaikaAuthenticationError(
                "MAIKA login did not return a valid user ID"
            ) from err

        try:
            expires_in = int(data.get("expire_time", 86400))
        except (TypeError, ValueError):
            expires_in = 86400
        self._token_valid_until = time.monotonic() + max(1, expires_in - 60)
        return data

    async def async_list_devices(self) -> list[dict[str, Any]]:
        """Return all MAIKA speakers registered to the account."""
        response = await self._async_request_json(
            "GET",
            f"{USERS_BASE_URL}/v1/user-device",
            params={"page": 1, "limit": 100},
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, list):
            raise MaikaConnectionError("Invalid device list response")
        return [
            item
            for item in data
            if isinstance(item, dict)
            and item.get("device_id")
            and item.get("type", "speaker") == "speaker"
        ]

    async def async_get_device(self, internal_id: int) -> dict[str, Any]:
        """Return detailed information for one speaker."""
        response = await self._async_request_json(
            "GET", f"{USERS_BASE_URL}/v1/user-device/{internal_id}"
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, dict):
            raise MaikaConnectionError("Invalid device detail response")
        return data

    async def async_get_tts_voices(self) -> list[dict[str, Any]]:
        """Return the selectable MAIKA TTS voices."""
        if self._voice_cache is not None:
            return self._voice_cache
        response = await self._async_request_json(
            "GET", f"{USERS_BASE_URL}/v1/user/tts_speaker_voices"
        )
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, list):
            raise MaikaConnectionError("Invalid TTS voice response")
        self._voice_cache = [item for item in data if isinstance(item, dict)]
        return self._voice_cache

    async def async_update_device(
        self,
        internal_id: int,
        serial_number: str,
        **changes: Any,
    ) -> dict[str, Any]:
        """Update writable speaker settings."""
        unsupported = set(changes) - REST_UPDATE_FIELDS
        if unsupported:
            raise ValueError(f"Unsupported MAIKA setting fields: {unsupported}")
        body = {
            "id": internal_id,
            "device_id": serial_number,
            **{key: value for key, value in changes.items() if value is not None},
        }
        return await self._async_request_json(
            "PUT",
            f"{USERS_BASE_URL}/v1/user-device/{internal_id}",
            json_body=body,
        )

    async def async_set_volume(self, serial_number: str, volume: int) -> None:
        """Set speaker playback volume from 0 to 100."""
        await self.async_send_command(
            "SetVolume",
            "SystemControl",
            {"deviceId": serial_number, "volume": max(0, min(100, volume))},
        )

    async def async_set_microphone_mute(self, serial_number: str, muted: bool) -> None:
        """Mute or unmute the physical speaker microphone."""
        await self.async_send_command(
            "Mute" if muted else "Unmute",
            "Recording",
            {"deviceId": serial_number},
        )

    async def async_playback_command(
        self,
        serial_number: str,
        command: str,
        song_key: str | None = None,
    ) -> None:
        """Send a playback controller command."""
        payload: dict[str, Any] = {"deviceId": serial_number}
        if song_key:
            payload["songKey"] = song_key
        await self.async_send_command(command, "PlaybackController", payload)

    async def async_cast_media(
        self,
        serial_number: str,
        media_url: str,
        *,
        title: str | None = None,
        media_type: str = "audio",
        stream_format: str = "AUDIO_MPEG",
        offset_milliseconds: int = 0,
    ) -> None:
        """Hand an audio URL from the app client to one physical speaker."""
        media_card = {
            "format": stream_format,
            "url": media_url,
            "type": media_type,
        }
        if title:
            media_card["title"] = title

        await self._async_send_stream_meta(
            {
                "event": {
                    "header": {
                        "messageId": f"messageId-{uuid4()}",
                        "name": "CommandHandOver",
                        "namespace": "SystemControl",
                    },
                    "payload": {
                        "fromDeviceId": self._client_id,
                        "messageInfo": {
                            "eventHeader": {
                                "dialogRequestId": str(uuid4()),
                                "messageId": f"messageId-{uuid4()}",
                                "name": "Play",
                                "namespace": "AudioPlayer",
                            },
                            "mediaCard": media_card,
                            "mediaOffset": max(0, offset_milliseconds),
                        },
                        "toDeviceId": [serial_number],
                    },
                }
            }
        )

    async def async_restart_device(self, serial_number: str) -> None:
        """Restart a speaker without exposing the destructive Reset command."""
        await self.async_send_command(
            "Reboot", "SystemControl", {"toDeviceId": serial_number}
        )

    async def async_start_conversation_listening(self, serial_number: str) -> None:
        """Ask MAIKA cloud to mirror one speaker conversation to this client."""
        await self.async_send_command(
            "StartListening",
            "Conversation",
            {"deviceId": serial_number, "type": "conversation"},
        )

    async def async_stop_conversation_listening(self, serial_number: str) -> None:
        """Stop mirroring one speaker conversation to this client."""
        await self.async_send_command(
            "StopListening",
            "Conversation",
            {"deviceId": serial_number, "type": "conversation"},
        )

    async def async_request_device_info(
        self, serial_number: str, timeout_seconds: float = 8.0
    ) -> dict[str, Any] | None:
        """Request live playback, volume and microphone state over /connect."""
        cached = self.live_device_info.get(serial_number)
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=timeout_seconds)
        except TimeoutError:
            return cached

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        waiters = self._device_info_waiters.setdefault(serial_number, [])
        waiters.append(future)
        try:
            await self.async_send_command(
                "GetDeviceInfo",
                "ClientInformation",
                {
                    "deviceId": serial_number,
                    "fields": DEVICE_INFO_FIELDS,
                },
            )
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        except TimeoutError:
            return self.live_device_info.get(serial_number, cached)
        finally:
            current_waiters = self._device_info_waiters.get(serial_number)
            if current_waiters and future in current_waiters:
                current_waiters.remove(future)
            if current_waiters == []:
                self._device_info_waiters.pop(serial_number, None)

    async def async_send_command(
        self,
        name: str,
        namespace: str,
        payload: dict[str, Any],
        *,
        retry_auth: bool = True,
    ) -> None:
        """Send one MAIKA speaker command through chatbot /stream."""
        await self._async_send_stream_meta(
            {
                "event": {
                    "header": {
                        "dialogRequestId": str(uuid4()),
                        "messageId": f"messageId-{uuid4()}",
                        "name": name,
                        "namespace": namespace,
                    },
                    "payload": payload,
                }
            },
            retry_auth=retry_auth,
        )

    async def _async_send_stream_meta(
        self,
        meta: dict[str, Any],
        *,
        retry_auth: bool = True,
    ) -> None:
        """Send an allowlisted MAIKA metadata envelope through chatbot /stream."""
        await self._async_ensure_authenticated()
        assert self._access_token is not None
        assert self._user_id is not None

        encoded_meta = base64.b64encode(
            json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode()
        ).decode()

        headers = self._stream_headers(encoded_meta)
        try:
            async with self._session.post(
                f"{CHATBOT_BASE_URL}/stream",
                headers=headers,
                data=b"",
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status == 401 and retry_auth:
                    await response.read()
                    self._clear_authentication()
                    await self._async_ensure_authenticated()
                    await self._async_send_stream_meta(meta, retry_auth=False)
                    return
                if response.status in (401, 403):
                    raise MaikaAuthenticationError(
                        "MAIKA command authentication failed"
                    )
                if response.status >= 400:
                    raise MaikaConnectionError(
                        f"MAIKA command returned HTTP {response.status}"
                    )
                body = await response.read()
        except MaikaApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MaikaConnectionError("Unable to send MAIKA command") from err

        if body:
            try:
                result = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return
            if isinstance(result, dict) and result.get("status") is False:
                raise MaikaConnectionError("MAIKA rejected the command")

    async def async_listen_forever(self) -> None:
        """Maintain the MAIKA /connect stream and decode framed JSON events."""
        retry_delay = 1
        while not self._stopping:
            try:
                self._connected.clear()
                await self._async_ensure_authenticated()
                assert self._access_token is not None
                async with self._session.get(
                    f"{CHATBOT_BASE_URL}/connect",
                    headers=self._connect_headers(),
                    timeout=STREAM_TIMEOUT,
                ) as response:
                    if response.status == 401:
                        self._clear_authentication()
                        raise MaikaAuthenticationError(
                            "MAIKA event stream authentication expired"
                        )
                    if response.status >= 400:
                        raise MaikaConnectionError(
                            f"MAIKA event stream returned HTTP {response.status}"
                        )

                    retry_delay = 1
                    buffer = ""
                    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                    async for chunk in response.content.iter_any():
                        if self._stopping:
                            return
                        buffer += decoder.decode(chunk)
                        frames, buffer = self._extract_frames(buffer)
                        for frame in frames:
                            self._handle_stream_frame(frame)
            except asyncio.CancelledError:
                raise
            except MaikaAuthenticationError:
                self._connected.clear()
                if self._stopping:
                    return
                try:
                    await self.async_login()
                except MaikaApiError as err:
                    _LOGGER.warning("Unable to reauthenticate MAIKA stream: %s", err)
            except (MaikaApiError, aiohttp.ClientError, TimeoutError) as err:
                self._connected.clear()
                if not self._stopping:
                    _LOGGER.debug("MAIKA event stream disconnected: %s", err)

            self._connected.clear()

            if not self._stopping:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    async def async_stop(self) -> None:
        """Stop background activity and release pending requests."""
        self._stopping = True
        self._connected.clear()
        for waiters in self._device_info_waiters.values():
            for future in waiters:
                if not future.done():
                    future.cancel()
        self._device_info_waiters.clear()
        if self._listener_task is not None and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

    async def _async_request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        await self._async_ensure_authenticated()
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=self._rest_headers(include_authorization=True),
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status == 401 and retry_auth:
                    await response.read()
                    self._clear_authentication()
                    await self._async_ensure_authenticated()
                    return await self._async_request_json(
                        method,
                        url,
                        params=params,
                        json_body=json_body,
                        retry_auth=False,
                    )
                if response.status in (401, 403):
                    await response.read()
                    raise MaikaAuthenticationError("MAIKA authentication failed")
                if response.status >= 400:
                    await response.read()
                    raise MaikaConnectionError(
                        f"MAIKA API returned HTTP {response.status}"
                    )
                payload = await self._read_json(response)
        except MaikaApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MaikaConnectionError("Unable to communicate with MAIKA") from err

        if not isinstance(payload, dict):
            raise MaikaConnectionError("MAIKA API returned invalid JSON")
        code = payload.get("code")
        if code not in (None, 0, 200):
            raise MaikaConnectionError(f"MAIKA API returned code {code}")
        return payload

    async def _async_ensure_authenticated(self) -> None:
        if self._access_token and time.monotonic() < self._token_valid_until:
            return
        async with self._auth_lock:
            if self._access_token and time.monotonic() < self._token_valid_until:
                return
            await self.async_login()

    def _clear_authentication(self) -> None:
        self._access_token = None
        self._token_valid_until = 0.0

    def _rest_headers(self, *, include_authorization: bool) -> dict[str, str]:
        headers = {
            "device-type": APP_DEVICE_TYPE,
            "version-info": APP_VERSION,
            "timezone": APP_TIMEZONE,
            "language-code": APP_LANGUAGE,
        }
        if include_authorization and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _connect_headers(self) -> dict[str, str]:
        assert self._access_token is not None
        return {
            "Authorization": self._access_token,
            "device-id": self._client_id,
            "device-type": APP_DEVICE_TYPE,
            "version-info": APP_VERSION,
            "olli-session-id": self._session_id,
            "timezone": APP_TIMEZONE,
            "source": APP_DEVICE_TYPE,
            "Content-Type": "application/octet-stream",
            "language-code": APP_LANGUAGE,
        }

    def _stream_headers(self, encoded_meta: str) -> dict[str, str]:
        assert self._access_token is not None
        assert self._user_id is not None
        return {
            "Authorization": self._access_token,
            "device-id": self._client_id,
            "device-type": APP_DEVICE_TYPE,
            "version-info": APP_VERSION,
            "olli-session-id": self._session_id,
            "source": APP_DEVICE_TYPE,
            "Content-Type": "application/octet-stream",
            "client-version": APP_VERSION,
            "user-id": str(self._user_id),
            "language-code": APP_LANGUAGE,
            "meta": encoded_meta,
        }

    @staticmethod
    async def _read_json(response: aiohttp.ClientResponse) -> Any:
        body = await response.read()
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise MaikaConnectionError("MAIKA returned a non-JSON response") from err

    @staticmethod
    def _extract_frames(buffer: str) -> tuple[list[dict[str, Any]], str]:
        frames: list[dict[str, Any]] = []
        while True:
            start = buffer.find(_FRAME_START)
            if start < 0:
                if len(buffer) > len(_FRAME_START):
                    buffer = buffer[-len(_FRAME_START) :]
                break
            end = buffer.find(_FRAME_END, start + len(_FRAME_START))
            if end < 0:
                buffer = buffer[start:]
                break
            raw_frame = buffer[start + len(_FRAME_START) : end].strip()
            buffer = buffer[end + len(_FRAME_END) :]
            if not raw_frame:
                continue
            try:
                frame = json.loads(raw_frame)
            except json.JSONDecodeError:
                continue
            if isinstance(frame, dict):
                frames.append(frame)
        if len(buffer) > _MAX_STREAM_BUFFER:
            buffer = buffer[-_MAX_STREAM_BUFFER:]
        return frames, buffer

    def _handle_stream_frame(self, frame: dict[str, Any]) -> None:
        if self._is_connect_frame(frame):
            if not self._connected.is_set():
                self._listener_generation += 1
            self._connected.set()
            self._dispatch_stream_frame(frame)
            return
        if "apiKeys" in frame:
            self._dispatch_stream_frame(frame)
            return

        normalized_frame = self._normalize_stream_frame(frame)
        header = normalized_frame.get("header")
        payload = normalized_frame.get("payload")
        if (
            isinstance(header, dict)
            and isinstance(payload, dict)
            and header.get("name") == "DeviceInfo"
            and header.get("namespace") == "ClientInformation"
        ):
            serial_number = payload.get("deviceId") or payload.get("device_id")
            if isinstance(serial_number, str) and serial_number:
                self.live_device_info[serial_number] = payload
                for future in self._device_info_waiters.pop(serial_number, []):
                    if not future.done():
                        future.set_result(payload)

        self._dispatch_stream_frame(normalized_frame)

    def _dispatch_stream_frame(self, frame: dict[str, Any]) -> None:
        """Forward one decoded frame without exposing it to logs."""
        if self._event_callback is not None:
            try:
                self._event_callback(frame)
            except Exception:
                _LOGGER.exception("Unable to handle a MAIKA cloud stream frame")

    @staticmethod
    def _is_connect_frame(frame: dict[str, Any]) -> bool:
        """Return whether a frame is the MAIKA connection handshake."""
        if frame.get("session_id"):
            return True
        if "connected" not in frame:
            return False
        header = frame.get("header")
        return isinstance(header, dict) and bool(
            header.get("sessionId") or header.get("session_id")
        )

    @staticmethod
    def _normalize_stream_frame(frame: dict[str, Any]) -> dict[str, Any]:
        """Unwrap known cloud envelopes until a directive header is found."""
        pending = [frame]
        seen: set[int] = set()
        while pending:
            candidate = pending.pop(0)
            candidate_id = id(candidate)
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            if isinstance(candidate.get("header"), dict):
                return candidate
            for key in _STREAM_WRAPPER_KEYS:
                nested = candidate.get(key)
                if isinstance(nested, dict):
                    pending.append(nested)
                elif isinstance(nested, list):
                    pending.extend(item for item in nested if isinstance(item, dict))
        return frame
