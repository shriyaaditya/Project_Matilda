import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.domain.resolution import CanonicalPerson, EntityResolution, ResolutionEvidence


class PersonRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_person_by_qid(self, wikidata_qid: str) -> CanonicalPersonModel | None:
        stmt = select(CanonicalPersonModel).where(CanonicalPersonModel.wikidata_qid == wikidata_qid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_person_by_name(self, canonical_name: str) -> CanonicalPersonModel | None:
        stmt = select(CanonicalPersonModel).where(
            CanonicalPersonModel.canonical_name.ilike(canonical_name.strip())
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_canonical_person(
        self,
        canonical_name: str,
        wikidata_qid: str | None = None,
        birth_year: int | None = None,
        death_year: int | None = None,
        occupations: list[str] | None = None,
        aliases: list[str] | None = None,
        description: str | None = None,
    ) -> CanonicalPersonModel:
        if wikidata_qid:
            existing = await self.get_person_by_qid(wikidata_qid)
            if existing:
                return existing

        person_model = CanonicalPersonModel(
            canonical_name=canonical_name,
            wikidata_qid=wikidata_qid,
            birth_year=birth_year,
            death_year=death_year,
            occupations=occupations or [],
            aliases=aliases or [],
            description=description,
        )
        self.db.add(person_model)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(person_model)
        return person_model

    async def count_resolutions_by_document(self, document_id: uuid.UUID) -> int:
        stmt = select(EntityResolutionModel).where(EntityResolutionModel.document_id == document_id)
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def delete_resolutions_by_document(self, document_id: uuid.UUID) -> None:
        stmt = delete(EntityResolutionModel).where(EntityResolutionModel.document_id == document_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def save_resolutions_batch(self, resolutions_domain: list[EntityResolution]) -> None:
        models = [
            EntityResolutionModel(
                id=r.id,
                mention_id=r.mention_id,
                document_id=r.document_id,
                person_id=r.person_id,
                status=r.status,
                resolution_score=r.resolution_score,
                matched_qid=r.matched_qid,
                evidence=r.evidence.model_dump(),
                created_at=r.created_at,
            )
            for r in resolutions_domain
        ]
        self.db.add_all(models)
        await self.db.commit()

    async def get_resolutions_by_document(
        self,
        document_id: uuid.UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EntityResolutionModel], int]:
        stmt = select(EntityResolutionModel).where(EntityResolutionModel.document_id == document_id)
        if status:
            stmt = stmt.where(EntityResolutionModel.status == status.upper())

        stmt = stmt.order_by(EntityResolutionModel.created_at.asc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        resolutions = list(result.scalars().all())

        count_stmt = select(EntityResolutionModel).where(EntityResolutionModel.document_id == document_id)
        if status:
            count_stmt = count_stmt.where(EntityResolutionModel.status == status.upper())
        count_res = await self.db.execute(count_stmt)
        total = len(list(count_res.scalars().all()))

        return resolutions, total

    async def get_people_by_document(
        self, document_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[CanonicalPersonModel], int]:
        stmt = (
            select(CanonicalPersonModel)
            .join(EntityResolutionModel, EntityResolutionModel.person_id == CanonicalPersonModel.id)
            .where(EntityResolutionModel.document_id == document_id)
            .distinct()
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        people = list(result.scalars().all())

        count_stmt = (
            select(CanonicalPersonModel)
            .join(EntityResolutionModel, EntityResolutionModel.person_id == CanonicalPersonModel.id)
            .where(EntityResolutionModel.document_id == document_id)
            .distinct()
        )
        count_res = await self.db.execute(count_stmt)
        total = len(list(count_res.scalars().all()))

        return people, total

    async def get_resolution_by_id(self, resolution_id: uuid.UUID) -> EntityResolutionModel | None:
        stmt = select(EntityResolutionModel).where(EntityResolutionModel.id == resolution_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def to_person_domain(model: CanonicalPersonModel) -> CanonicalPerson:
        return CanonicalPerson(
            id=model.id,
            canonical_name=model.canonical_name,
            wikidata_qid=model.wikidata_qid,
            birth_year=model.birth_year,
            death_year=model.death_year,
            occupations=model.occupations or [],
            aliases=model.aliases or [],
            description=model.description,
            created_at=model.created_at,
        )

    @staticmethod
    def to_resolution_domain(model: EntityResolutionModel) -> EntityResolution:
        evidence_obj = ResolutionEvidence(**model.evidence)
        return EntityResolution(
            id=model.id,
            mention_id=model.mention_id,
            document_id=model.document_id,
            person_id=model.person_id,
            status=model.status,
            resolution_score=model.resolution_score,
            matched_qid=model.matched_qid,
            evidence=evidence_obj,
            created_at=model.created_at,
        )
