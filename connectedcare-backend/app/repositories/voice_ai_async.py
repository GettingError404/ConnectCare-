from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_ai import (
    AIVoiceResponse,
    AudioChunk,
    AudioSession,
    NLPResult,
    RealtimeVoiceEvent,
    STTResult,
    TTSOutput,
    Translation,
)


class VoiceAIRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_audio_session(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        conversation_id: UUID | None,
        language: str | None,
        source_language: str | None,
        target_language: str | None,
        metadata: dict | None,
    ) -> AudioSession:
        entity = AudioSession(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            language=language,
            source_language=source_language,
            target_language=target_language,
            metadata_json=metadata,
            heartbeat_at=datetime.now(timezone.utc),
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get_audio_session(self, *, tenant_id: UUID, session_id: UUID) -> AudioSession | None:
        stmt = select(AudioSession).where(
            AudioSession.tenant_id == tenant_id,
            AudioSession.id == session_id,
            AudioSession.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_heartbeat(self, *, tenant_id: UUID, session_id: UUID) -> None:
        await self.session.execute(
            update(AudioSession)
            .where(AudioSession.tenant_id == tenant_id, AudioSession.id == session_id)
            .values(heartbeat_at=datetime.now(timezone.utc))
        )

    async def add_audio_chunk(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        chunk_index: int,
        sequence_no: int,
        duration_ms: int | None,
        mime_type: str | None,
        audio_blob: bytes,
        metadata: dict | None,
    ) -> AudioChunk:
        entity = AudioChunk(
            tenant_id=tenant_id,
            session_id=session_id,
            chunk_index=chunk_index,
            sequence_no=sequence_no,
            duration_ms=duration_ms,
            mime_type=mime_type,
            audio_blob=audio_blob,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_stt_result(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        chunk_id: UUID | None,
        provider: str,
        model: str,
        transcript: str,
        is_partial: bool,
        confidence: float | None,
        detected_language: str | None,
        metadata: dict | None,
    ) -> STTResult:
        entity = STTResult(
            tenant_id=tenant_id,
            session_id=session_id,
            chunk_id=chunk_id,
            provider=provider,
            model=model,
            transcript=transcript,
            is_partial=is_partial,
            confidence=confidence,
            detected_language=detected_language,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_translation(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID | None,
        stt_result_id: UUID | None,
        provider: str,
        source_language: str,
        target_language: str,
        source_text: str,
        translated_text: str,
        confidence: float | None,
        metadata: dict | None,
    ) -> Translation:
        entity = Translation(
            tenant_id=tenant_id,
            session_id=session_id,
            stt_result_id=stt_result_id,
            provider=provider,
            source_language=source_language,
            target_language=target_language,
            source_text=source_text,
            translated_text=translated_text,
            confidence=confidence,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_nlp_result(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID | None,
        stt_result_id: UUID | None,
        translation_id: UUID | None,
        intent: str | None,
        entities: dict | None,
        sentiment: str | None,
        confidence: float | None,
        healthcare_flags: dict | None,
        metadata: dict | None,
    ) -> NLPResult:
        entity = NLPResult(
            tenant_id=tenant_id,
            session_id=session_id,
            stt_result_id=stt_result_id,
            translation_id=translation_id,
            intent=intent,
            entities=entities,
            sentiment=sentiment,
            confidence=confidence,
            healthcare_flags=healthcare_flags,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_tts_output(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID | None,
        provider: str,
        model: str,
        voice: str | None,
        language: str | None,
        text_input: str,
        audio_blob: bytes,
        duration_ms: int | None,
        metadata: dict | None,
    ) -> TTSOutput:
        entity = TTSOutput(
            tenant_id=tenant_id,
            session_id=session_id,
            provider=provider,
            model=model,
            voice=voice,
            language=language,
            text_input=text_input,
            audio_blob=audio_blob,
            duration_ms=duration_ms,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def add_ai_voice_response(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        stt_result_id: UUID | None,
        translation_id: UUID | None,
        nlp_result_id: UUID | None,
        tts_output_id: UUID | None,
        prompt_context: str | None,
        response_text: str,
        retrieval_metadata: dict | None,
        latency_ms: int | None,
        metadata: dict | None,
    ) -> AIVoiceResponse:
        entity = AIVoiceResponse(
            tenant_id=tenant_id,
            session_id=session_id,
            stt_result_id=stt_result_id,
            translation_id=translation_id,
            nlp_result_id=nlp_result_id,
            tts_output_id=tts_output_id,
            prompt_context=prompt_context,
            response_text=response_text,
            retrieval_metadata=retrieval_metadata,
            latency_ms=latency_ms,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def next_event_sequence(self, *, tenant_id: UUID, session_id: UUID) -> int:
        stmt = select(func.max(RealtimeVoiceEvent.sequence_no)).where(
            RealtimeVoiceEvent.tenant_id == tenant_id,
            RealtimeVoiceEvent.session_id == session_id,
        )
        max_seq = (await self.session.execute(stmt)).scalar_one_or_none()
        return int(max_seq or 0) + 1

    async def add_realtime_event(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        event_type: str,
        event_payload: dict,
    ) -> RealtimeVoiceEvent:
        seq = await self.next_event_sequence(tenant_id=tenant_id, session_id=session_id)
        entity = RealtimeVoiceEvent(
            tenant_id=tenant_id,
            session_id=session_id,
            sequence_no=seq,
            event_type=event_type,
            event_payload=event_payload,
            sent_at=datetime.now(timezone.utc),
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_events_since(self, *, tenant_id: UUID, session_id: UUID, from_sequence: int) -> list[RealtimeVoiceEvent]:
        stmt = (
            select(RealtimeVoiceEvent)
            .where(
                RealtimeVoiceEvent.tenant_id == tenant_id,
                RealtimeVoiceEvent.session_id == session_id,
                RealtimeVoiceEvent.sequence_no > from_sequence,
            )
            .order_by(RealtimeVoiceEvent.sequence_no.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def conversation_history(self, *, tenant_id: UUID, session_id: UUID) -> dict:
        stt = (
            select(STTResult)
            .where(STTResult.tenant_id == tenant_id, STTResult.session_id == session_id)
            .order_by(STTResult.created_at.asc())
        )
        translations = (
            select(Translation)
            .where(Translation.tenant_id == tenant_id, Translation.session_id == session_id)
            .order_by(Translation.created_at.asc())
        )
        nlp = (
            select(NLPResult)
            .where(NLPResult.tenant_id == tenant_id, NLPResult.session_id == session_id)
            .order_by(NLPResult.created_at.asc())
        )
        responses = (
            select(AIVoiceResponse)
            .where(AIVoiceResponse.tenant_id == tenant_id, AIVoiceResponse.session_id == session_id)
            .order_by(AIVoiceResponse.created_at.asc())
        )

        stt_rows = list((await self.session.execute(stt)).scalars().all())
        trans_rows = list((await self.session.execute(translations)).scalars().all())
        nlp_rows = list((await self.session.execute(nlp)).scalars().all())
        resp_rows = list((await self.session.execute(responses)).scalars().all())

        return {
            "stt_results": [
                {
                    "id": str(r.id),
                    "transcript": r.transcript,
                    "is_partial": r.is_partial,
                    "confidence": r.confidence,
                    "detected_language": r.detected_language,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in stt_rows
            ],
            "translations": [
                {
                    "id": str(r.id),
                    "source_language": r.source_language,
                    "target_language": r.target_language,
                    "translated_text": r.translated_text,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in trans_rows
            ],
            "nlp_results": [
                {
                    "id": str(r.id),
                    "intent": r.intent,
                    "sentiment": r.sentiment,
                    "entities": r.entities,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in nlp_rows
            ],
            "ai_responses": [
                {
                    "id": str(r.id),
                    "response_text": r.response_text,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in resp_rows
            ],
        }

    async def analytics(self, *, tenant_id: UUID) -> dict:
        async def _count(model):
            stmt = select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
            return int((await self.session.execute(stmt)).scalar() or 0)

        total_sessions = await _count(AudioSession)
        total_audio_chunks = await _count(AudioChunk)
        total_stt_results = await _count(STTResult)
        total_translations = await _count(Translation)
        total_nlp_results = await _count(NLPResult)
        total_tts_outputs = await _count(TTSOutput)
        total_ai_responses = await _count(AIVoiceResponse)

        avg_latency_stmt = select(func.avg(AIVoiceResponse.latency_ms)).where(AIVoiceResponse.tenant_id == tenant_id)
        avg_latency = float((await self.session.execute(avg_latency_stmt)).scalar() or 0.0)

        return {
            "total_sessions": total_sessions,
            "total_audio_chunks": total_audio_chunks,
            "total_stt_results": total_stt_results,
            "total_translations": total_translations,
            "total_nlp_results": total_nlp_results,
            "total_tts_outputs": total_tts_outputs,
            "total_ai_responses": total_ai_responses,
            "avg_response_latency_ms": avg_latency,
        }
