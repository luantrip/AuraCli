"""
Skill Retriever with RAG (Retrieval-Augmented Generation).

This module provides semantic search over the skills knowledge base.
It acts as a client to a standalone embedding server, which provides
the sentence embeddings. This architecture isolates heavy ML models
into a separate process, enhancing stability.
"""

import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests
import yaml

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.embeddings import EMBEDDING_SERVER_PORT
from aura_cli.core.personas.models import SkillMatch, SkillMetadata

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent / "skills"
NATIVE_SKILLS_DIR = Path(__file__).parents[1] / "skills"
EMBEDDING_SERVER_URL = f"http://127.0.0.1:{EMBEDDING_SERVER_PORT}/embed"


class SkillRetriever:
    """
    Retrieves relevant skills using semantic similarity via an external embedding server.
    Falls back to keyword matching if the server is unavailable.
    """

    def __init__(
        self, skills_dir: Optional[Path] = None, include_installed: bool = False
    ):
        """
        Initialize skill retriever.
        Args:
            skills_dir: Directory containing skill markdown files.
        """
        self._using_default_skills_dir = skills_dir is None
        self.skills_dir = skills_dir or SKILLS_DIR
        self._additional_skill_dirs = []
        if include_installed:
            self._additional_skill_dirs = [
                ArtifactLayout().user("skills"),
                ArtifactLayout().project("skills"),
            ]
        self._embeddings_cache: Dict[str, List[float]] = {}
        self._query_embeddings_cache: Dict[str, List[float]] = {}
        self._skills: List[SkillMetadata] = []
        self._embedding_server_ok = (
            True  # Assume server is available until a request fails
        )
        self._load_skills()
        if self._using_default_skills_dir:
            self._load_skill_directory(NATIVE_SKILLS_DIR)
        for directory in self._additional_skill_dirs:
            self._load_skill_directory(directory)

    def _load_skills(self) -> None:
        """Load skill metadata from markdown files."""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return
        self._load_skill_directory(self.skills_dir)

    def _load_skill_directory(self, directory: Path) -> None:
        if not directory.exists():
            return
        for md_file in directory.glob("**/*.md"):
            try:
                metadata = self._parse_skill_file(md_file)
                if metadata:
                    self._skills.append(metadata)
            except Exception as e:
                logger.error(f"Error loading skill {md_file}: {e}")
        logger.info(f"Loaded {len(self._skills)} skills")

    def _parse_skill_file(self, filepath: Path) -> Optional[SkillMetadata]:
        """Parse skill file and extract metadata."""
        content = filepath.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        try:
            frontmatter = yaml.safe_load(parts[1])
            if not frontmatter or "name" not in frontmatter:
                return None
            return SkillMetadata(
                name=frontmatter.get("name", filepath.stem),
                description=frontmatter.get("description", ""),
                version=frontmatter.get("version", "1.0.0"),
                author=frontmatter.get("author", "Aura Core Team"),
                filepath=filepath,
            )
        except yaml.YAMLError as e:
            logger.error(f"YAML error in {filepath}: {e}")
            return None

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors using numpy."""
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _compute_embedding(self, text: str) -> Optional[List[float]]:
        """Compute embedding for text by calling the embedding server."""
        if not self._embedding_server_ok:
            # Try to reactivate periodically (server may have finished loading)
            if not hasattr(self, "_last_server_retry"):
                self._last_server_retry = 0.0
            import time

            if time.monotonic() - self._last_server_retry > 30.0:
                self._embedding_server_ok = True
                self._last_server_retry = time.monotonic()
                logger.debug("Tentando reconectar ao servidor de embeddings...")
            else:
                return None
        try:
            response = requests.post(
                EMBEDDING_SERVER_URL, json={"text": text}, timeout=3
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding")
            if isinstance(embedding, list):
                return embedding
            logger.warning("Embedding server returned invalid data.")
            return None
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            err_str = str(e).strip()
            # Connection refused/timeout = server still starting, retry later
            is_connection_err = any(
                x in err_str.lower()
                for x in [
                    "connection refused",
                    "max retries",
                    "connect",
                    "timeout",
                    "timed out",
                ]
            )
            if is_connection_err:
                logger.debug(
                    f"Embeddings indisponível (servidor iniciando?): {err_str[:60]}"
                )
                # Do not disable permanently — server may be loading the model
                return None
            # 503 = server up but model still loading
            if "503" in err_str or "Service Unavailable" in err_str:
                logger.debug(
                    "Embeddings: servidor up mas modelo ainda carregando (503)."
                )
                return None
            # Other errors (404, invalid JSON, etc.) = disable for the session
            logger.warning(
                f"Embeddings indisponível: {err_str[:60]}. Busca por palavras-chave."
            )
            self._embedding_server_ok = False
            return None

    def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached embedding for a query.

        Only caches successful (non-None) results so that after the embedding
        server recovers, subsequent calls retry rather than returning a stale None.
        """
        if len(self._query_embeddings_cache) > 100:
            keys_to_remove = list(self._query_embeddings_cache.keys())[:50]
            for key in keys_to_remove:
                del self._query_embeddings_cache[key]
        if query not in self._query_embeddings_cache:
            result = self._compute_embedding(query)
            if result is not None:
                self._query_embeddings_cache[query] = result
            return result
        return self._query_embeddings_cache[query]

    def _get_skill_embedding(self, skill: SkillMetadata) -> Optional[List[float]]:
        """Get cached embedding for a skill description.

        Only caches successful (non-None) results so that after the embedding
        server recovers, subsequent calls retry rather than returning a stale None.
        """
        if skill.name not in self._embeddings_cache:
            result = self._compute_embedding(skill.description)
            if result is not None:
                self._embeddings_cache[skill.name] = result
            return result
        return self._embeddings_cache[skill.name]

    def _keyword_score(self, query: str, skill: SkillMetadata) -> float:
        """Compute keyword-based similarity score."""
        query_words = set(re.findall(r"\w+", query.lower()))
        desc_words = set(re.findall(r"\w+", skill.description.lower()))
        name_words = set(re.findall(r"\w+", skill.name.lower()))
        all_skill_words = desc_words | name_words
        if not all_skill_words:
            return 0.0
        matches = len(query_words & all_skill_words)
        return matches / max(len(query_words), 1)

    def find_all_matches(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.3,
    ) -> List[SkillMatch]:
        """Find all matching skills above a threshold, sorted by score."""
        matches: List[Tuple[float, SkillMetadata]] = []

        if self._embedding_server_ok:
            try:
                query_embedding = self._get_query_embedding(query)
                if query_embedding:
                    for skill in self._skills:
                        skill_embedding = self._get_skill_embedding(skill)
                        if skill_embedding:
                            score = self._cosine_similarity(
                                query_embedding, skill_embedding
                            )
                            if score >= threshold:
                                matches.append((score, skill))
            except Exception as e:
                logger.error(f"Semantic search failed unexpectedly: {e}")

        if not matches:
            for skill in self._skills:
                score = self._keyword_score(query, skill)
                if score >= threshold:
                    matches.append((score, skill))

        matches.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, skill in matches[:limit]:
            content = (
                skill.filepath.read_text(encoding="utf-8") if skill.filepath else ""
            )
            results.append(SkillMatch(skill=skill, score=score, content=content))

        return results

    def find_best_match(
        self,
        query: str,
        threshold: float = 0.4,
    ) -> Optional[SkillMatch]:
        """Find the single best matching skill."""
        all_matches = self.find_all_matches(query, limit=1, threshold=threshold)
        return all_matches[0] if all_matches else None

    def find_relevant_skill(
        self,
        query: str,
        threshold: float = 0.4,
    ) -> Optional[str]:
        """Find the content of the most relevant skill."""
        match = self.find_best_match(query, threshold)
        return match.content if match else None

    def list_skills(self) -> List[SkillMetadata]:
        """List all available skills."""
        return self._skills.copy()

    def get_skill_by_name(self, name: str) -> Optional[str]:
        """Get skill content by exact name."""
        for skill in self._skills:
            if skill.name.lower() == name.lower():
                return (
                    skill.filepath.read_text(encoding="utf-8")
                    if skill.filepath
                    else None
                )
        return None

    def reload(self) -> None:
        """Reload skills from disk."""
        self._skills.clear()
        self._embeddings_cache.clear()
        self._query_embeddings_cache.clear()
        self._embedding_server_ok = True  # Reset server status on reload
        self._load_skills()


_retriever: Optional[SkillRetriever] = None


def get_skill_retriever() -> SkillRetriever:
    """Get the global SkillRetriever instance."""
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.SKILL_RETRIEVER):
            return container.resolve(Services.SKILL_RETRIEVER)
    except Exception:
        pass

    # Fallback to legacy singleton
    global _retriever
    if _retriever is None:
        _retriever = SkillRetriever()
    return _retriever
